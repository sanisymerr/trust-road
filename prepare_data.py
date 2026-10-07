"""Подготовка данных проекта ЦУР 3 из сохранённых исходных таблиц."""
from pathlib import Path
import json
import pandas as pd
import numpy as np

BASE = Path(__file__).resolve().parent
RAW = BASE / 'data' / 'raw'
OUT = BASE / 'data' / 'processed'
MISSING = {'…', '...', '—', '-', '–', '', 'нет данных'}
DISTRICTS = {'Центральный федеральный округ': 'ЦФО',
 'Северо-Западный федеральный округ': 'СЗФО', 'Южный федеральный округ': 'ЮФО',
 'Северо-Кавказский федеральный округ': 'СКФО', 'Приволжский федеральный округ': 'ПФО',
 'Уральский федеральный округ': 'УФО', 'Сибирский федеральный округ': 'СФО',
 'Дальневосточный федеральный округ': 'ДФО'}
METRICS = [
 ('opzh', 'Ожидаемая продолжительность жизни при рождении, все население', 'всего'),
 ('opzh', 'Ожидаемая продолжительность жизни при рождении, мужчины', 'мужчины'),
 ('opzh', 'Ожидаемая продолжительность жизни при рождении, женщины', 'женщины'),
 ('inf_mort', 'Коэффициент младенческой смертности', 'всего'),
 ('under5_mort', 'Коэффициент смертности детей до 5 лет', 'всего'),
 ('mat_mort', 'Коэффициент материнской смертности', 'всего'),
 ('mat_deaths', 'Число умерших женщин от материнских причин', 'всего'),
 ('births', 'Число родившихся', 'всего'), ('deaths', 'Число умерших', 'всего'),
 ('nat_inc', 'Естественный прирост (убыль) населения', 'всего'),
 ('cdr', 'Общий коэффициент смертности', 'всего')]
CODE_MAP = {label:(code,sex) for code,label,sex in METRICS}

def to_number(value):
    if pd.isna(value):
        return np.nan
    text = str(value).replace('\u00a0', ' ').replace('\u202f', ' ').strip().rstrip('*').strip()
    if text in MISSING:
        return np.nan
    return float(text.replace(' ', '').replace(',', '.').replace('−', '-'))

def build():
    OUT.mkdir(parents=True, exist_ok=True)
    raw_rf = pd.read_csv(RAW / 'rosstat_rf_zdorovie.csv', sep=';', dtype=str)
    rf = raw_rf.melt(id_vars=['Показатель','Ед. изм.'], var_name='year', value_name='raw_value')
    rf['year'] = rf['year'].str.extract(r'(\d{4})',expand=False).astype(int)
    rf['code'] = rf['Показатель'].map(lambda x: CODE_MAP[x][0])
    rf['sex'] = rf['Показатель'].map(lambda x: CODE_MAP[x][1])
    rf['unit'] = rf['Ед. изм.']
    rf['value'] = rf['raw_value'].map(to_number)
    rf['preliminary'] = rf['raw_value'].str.endswith('*')
    rf['territory'],rf['type'],rf['district'] = 'Российская Федерация','country','РФ'
    if rf.duplicated(['year','code','sex']).any():
        raise ValueError('Повтор ключа в национальной таблице')
    wide = rf.assign(col=rf['code'] + rf['sex'].map({'всего':'','мужчины':'_m','женщины':'_f'})).pivot(index='year',columns='col',values='value')
    wide['gender_gap'] = wide['opzh_f'] - wide['opzh_m']
    wide = wide.reset_index()

    raw_reg = pd.read_csv(RAW / 'rosstat_opzh_regiony.csv',sep=';',dtype=str)
    raw_reg['territory'] = raw_reg['Субъект'].str.replace('\u00a0',' ').str.replace(r'\s+',' ',regex=True).str.strip()
    district = 'РФ'
    records = []
    # Областные итоги включают автономные округа. Для сравнения берём
    # исходные строки без округов и отдельно сами автономные округа.
    replacements = {'Архангельская область': ('Архангельская область без автономного округа','Архангельская область (без Ненецкого АО)'),
                    'Тюменская область': ('Тюменская область без автономных округов','Тюменская область (без ХМАО и ЯНАО)')}
    for _, row in raw_reg.iterrows():
        name = row['territory']
        if name == 'Российская Федерация':
            kind, d = 'country', 'РФ'
        elif name in DISTRICTS:
            district = DISTRICTS[name]
            kind, d = 'district', district
        elif 'без автономн' in name:
            continue
        else:
            kind, d = 'region', district
        source_row, source_name = row, name
        if name in replacements:
            old_name, name = replacements[name]
            match = raw_reg.loc[raw_reg['territory']==old_name]
            if len(match)!=1:
                raise ValueError('Не найдена единственная строка без АО')
            source_row = match.iloc[0]
            source_name = old_name
        records.append({'territory':name,'source_territory':source_name,'type':kind,'district':d,
                        **{str(y):to_number(source_row[str(y)]) for y in (2015,2019,2021)}})
    regions = pd.DataFrame(records)
    regions['change_2015_2019'] = regions['2019'] - regions['2015']
    regions['change_2019_2021'] = regions['2021'] - regions['2019']
    regions['deviation_2021'] = regions['2021'] - float(wide.loc[wide.year==2021,'opzh'].iloc[0])
    regions['rank_2021'] = np.nan
    idx = regions.type=='region'
    regions.loc[idx,'rank_2021'] = regions.loc[idx,'2021'].rank(ascending=False,method='min')
    q1,q3 = regions.loc[idx,'2021'].quantile([.25,.75])
    low,high = q1-1.5*(q3-q1),q3+1.5*(q3-q1)
    regions['outlier_2021'] = idx & ((regions['2021']<low)|(regions['2021']>high))
    regions['group_2021'] = np.where(regions.deviation_2021>=1,'Выше РФ на 1 год и более',np.where(regions.deviation_2021<=-1,'Ниже РФ на 1 год и более','Разница меньше 1 года'))

    columns = ['territory','type','district','year','code','sex','unit','value','preliminary']
    reg_long = regions.loc[regions.type!='country'].melt(id_vars=['territory','type','district'],value_vars=['2015','2019','2021'],var_name='year',value_name='value')
    reg_long['year'] = reg_long.year.astype(int)
    reg_long['code'],reg_long['sex'],reg_long['unit'],reg_long['preliminary'] = 'opzh','всего','лет',False
    gap = wide[['year','gender_gap']].rename(columns={'gender_gap':'value'})
    gap['territory'],gap['type'],gap['district'],gap['code'],gap['sex'],gap['unit'],gap['preliminary'] = 'Российская Федерация','country','РФ','gender_gap','всего','лет',False
    long = pd.concat([rf[columns],reg_long[columns],gap[columns]],ignore_index=True).sort_values(['territory','code','sex','year'])
    long['change_abs'],long['growth_pct'],long['index_2015'] = np.nan,np.nan,np.nan
    # Цепные показатели считаем лишь для ежегодных рядов РФ.
    for (territory,code,sex), part in long[long.type=='country'].groupby(['territory','code','sex']):
        values = part.value
        long.loc[part.index,'change_abs'] = values.diff()
        if code not in {'nat_inc','gender_gap'}:
            long.loc[part.index,'growth_pct'] = values.pct_change(fill_method=None)*100
            base = part.loc[part.year==2015,'value'].iloc[0]
            if pd.notna(base) and base!=0:
                long.loc[part.index,'index_2015'] = values/base*100
    if long.duplicated(['territory','year','code','sex']).any():
        raise ValueError('Повтор ключа итогового датасета')
    control = wide.births-wide.deaths-wide.nat_inc
    mm = wide.mat_deaths/wide.births*100000-wide.mat_mort
    valid_gender = wide[['opzh','opzh_m','opzh_f']].dropna()
    checks = [
      {'check':'Родившиеся - умершие = естественный прирост','passed':bool((control==0).all()),'detail':f'10 лет; максимальное расхождение {control.abs().max():.0f} человек'},
      {'check':'Пересчёт материнской смертности','passed':bool((mm.dropna().abs()<=.1).all()),'detail':f'{mm.notna().sum()} лет; максимальное расхождение {mm.abs().max():.3f} на 100 000'},
      {'check':'ОПЖ всего между мужским и женским значением','passed':bool(((valid_gender.opzh>=valid_gender.opzh_m)&(valid_gender.opzh<=valid_gender.opzh_f)).all()),'detail':f'{len(valid_gender)} лет'},
      {'check':'Совпадение РФ в национальной и региональной таблицах','passed':bool(all(abs(regions.loc[regions.type=='country',str(y)].iloc[0]-wide.loc[wide.year==y,'opzh'].iloc[0])<1e-9 for y in [2015,2019,2021])),'detail':'2015, 2019, 2021'},
      {'check':'Уникальные ключи итоговой таблицы','passed':not long.duplicated(['territory','year','code','sex']).any(),'detail':f'{len(long)} строк'},
      {'check':'Неперекрывающиеся территории сравнения','passed':bool(idx.sum()==85 and not regions.territory.isin(replacements).any()),'detail':'85 территорий; областные строки без АО явно подписаны'},
      {'check':'ОПЖ в проверочном диапазоне 55-90 лет','passed':bool(regions[['2015','2019','2021']].stack().between(55,90).all()),'detail':'Выбросы по IQR сохранены; диапазон не доказывает достоверность источника'},
      {'check':'Неотрицательные коэффициенты и числа событий','passed':bool((wide[['inf_mort','under5_mort','mat_mort','mat_deaths','births','deaths','cdr']].stack()>=0).all()),'detail':'Естественный прирост может быть отрицательным'}]
    if not all(c['passed'] for c in checks):
        raise ValueError('Проверки согласованности не пройдены')
    for frame,name in [(wide,'russia.csv'),(regions,'regions.csv'),(long,'long.csv'),(pd.DataFrame(checks),'validation.csv')]:
        frame.to_csv(OUT/name,index=False,encoding='utf-8-sig',float_format='%.8f')
    subjects = regions[idx]
    summary = {'years':[2015,2024],'territories':int(idx.sum()),'rows':len(long),'missing_values':int(long.value.isna().sum()),
      'opzh_2024':float(wide.loc[wide.year==2024,'opzh'].iloc[0]),'opzh_2015_2019_change':float(wide.loc[wide.year==2019,'opzh'].iloc[0]-wide.loc[wide.year==2015,'opzh'].iloc[0]),
      'target_gap_2024':78-float(wide.loc[wide.year==2024,'opzh'].iloc[0]),
      'infant_change_pct':float((wide.loc[wide.year==2024,'inf_mort'].iloc[0]/wide.loc[wide.year==2015,'inf_mort'].iloc[0]-1)*100),
      'regional_spread_2021':float(subjects['2021'].max()-subjects['2021'].min()),
      'regional_correlation':float(subjects['2019'].corr(subjects.change_2019_2021)),
      'iqr_bounds_2021':[float(low),float(high)],'outliers_2021':subjects.loc[subjects.outlier_2021,'territory'].tolist(),
      'primorye':subjects.loc[subjects.territory=='Приморский край'].iloc[0].to_dict(),
      'checks':checks}
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    payload={'russia':json.loads(wide.to_json(orient='records')),'regions':json.loads(regions.to_json(orient='records')),
             'long':json.loads(long.to_json(orient='records')),'summary':summary}
    (OUT/'dashboard_data.json').write_text(json.dumps(payload,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k not in ['checks','primorye','outliers_2021']},ensure_ascii=False,indent=2))
    return wide, regions, long

if __name__=='__main__':
    build()
