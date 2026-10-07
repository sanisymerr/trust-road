from pathlib import Path
import json
import html as html_lib
from plotly.offline import get_plotlyjs

PROJECT=Path(__file__).resolve().parent
def build():
    template=(PROJECT/'dashboard/template.html').read_text(encoding='utf-8')
    payload=(PROJECT/'data/processed/dashboard_data.json').read_text(encoding='utf-8').replace('</','<\\/')
    d=json.loads(payload)
    rf={r['year']:r for r in d['russia']}
    def f(x,n=2):return f'{x:,.{n}f}'.replace(',',' ').replace('.',',')
    subjects=[r for r in d['regions'] if r['type']=='region']
    prim=next(r for r in subjects if r['territory']=='Приморский край')
    high=max(subjects,key=lambda r:r['2021']);low=min(subjects,key=lambda r:r['2021'])
    conclusion=f'''<h2>Основные результаты</h2>
    <p>За 2015–2019 годы ОПЖ России выросла с {f(rf[2015]['opzh'])} до {f(rf[2019]['opzh'])} года.
    В 2021 году показатель составил {f(rf[2021]['opzh'])}, в 2023 году достиг максимума рассматриваемого ряда — {f(rf[2023]['opzh'])}.
    Значение 2024 года — {f(rf[2024]['opzh'])} года.</p>
    <p>Младенческая смертность снизилась с 6,5 до 4,0 на 1 000 родившихся живыми (−38,5%).
    Смертность детей до пяти лет снизилась с 8,0 в 2015 до 5,3 в 2023 году (−33,8%).</p>
    <p>Материнская смертность достигла 34,5 на 100 000 в 2021 году. В 2024 году показатель равен 11,2 по ЕМИСС 57314.
    Он ниже пикового значения и выше 9,0 в 2019 году. Разрыв ОПЖ женщин и мужчин в 2023 году составил {f(rf[2023]['gender_gap'])} года.</p>
    <p>В 2021 году разница ОПЖ территорий составила {f(high['2021']-low['2021'])} года: {high['territory']} — {f(high['2021'])},
    {low['territory']} — {f(low['2021'])}. Приморский край — {f(prim['2021'])} года, на {f(-prim['deviation_2021'])} года ниже России;
    место {int(prim['rank_2021'])} из 85.</p>
    <p>Естественная убыль 2024 года — 596 227 человек: разница между рождениями и смертями, без миграции.</p>
    <h2>Национальная цель: 78 лет к 2030 году</h2><p>От уровня 2024 года до ориентира остаётся 5,16 года.
    Условный линейный сценарий: 0,86 года в год до 2030 года.
    Для сравнения, средний прирост за 2015–2019 годы — 0,49 года в год.</p>
    <p class="small muted">Итоги за 2015–2024 годы. Для своего среза используйте разделы «Россия» и «Регионы».</p>'''
    manifest=json.loads((PROJECT/'data/sources/source_manifest.json').read_text(encoding='utf-8'))
    titles={'opzh':'ОПЖ России и территорий — ЕМИСС 31293','birthdeath':'Естественное движение населения, 2015–2023','birthdeath2024':'Естественное движение населения, 2024','infant':'Младенческая смертность, 2015–2022','infant2023':'Младенческая смертность, 2023 — Ежегодник 2024','infant2024':'Младенческая смертность, 2024 — Регионы России 2025','maternal':'Материнская смертность — ЕМИСС 57314','maternalcount':'Число материнских смертей, 2015–2022','maternalcount2023':'Число материнских смертей, 2023','under5':'Смертность детей до пяти лет — ЕМИСС 58536','opzh2024_preliminary':'ОПЖ 2024 — Волгоградская область в цифрах'}
    sources='<p class="small muted">Росстат и ЕМИСС · данные получены 07.10.2026</p><ol>'+''.join(f'<li><a href="{html_lib.escape(r["source_url"],quote=True)}">{html_lib.escape(titles.get(r["id"],r["id"]))}</a></li>' for r in manifest['sources'])+'</ol><p><a href="https://rosstat.gov.ru/sdg/data/goal3">Росстат. Показатели ЦУР 3</a> · <a href="https://unstats.un.org/sdgs/metadata/">ООН. Метаданные индикаторов</a></p>'
    html=template.replace('__PLOTLY__',get_plotlyjs()).replace('__DATA__',payload).replace('__SOURCES_HTML__',sources).replace('__CONCLUSIONS_HTML__',conclusion).replace('__LOCALE_RU__',(PROJECT/'dashboard/plotly-locale-ru.js').read_text(encoding='utf-8')).replace('__GLOBE__',(PROJECT/'dashboard/globe.svg').read_text(encoding='utf-8'))
    for token, name in [('__CONTROLS_JS__','controls.js'),('__CONTROLS_CSS__','controls.css'),('__GLOBE_MOTION_JS__','globe-motion.js'),('__GLOBE_MOTION_CSS__','globe-motion.css'),('__POLISH_JS__','polish.js'),('__POLISH_CSS__','polish.css')]:
        html=html.replace(token,(PROJECT/'dashboard'/name).read_text(encoding='utf-8'))
    (PROJECT/'dashboard/index.html').write_text(html,encoding='utf-8')
    print('Автономный дашборд:',len(html),'символов')
if __name__=='__main__':
    build()
