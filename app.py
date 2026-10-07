"""Учебный интерактивный дашборд ЦУР 3. Запуск: streamlit run app.py."""

from pathlib import Path
import json
import inspect

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "processed"
BLUE, ORANGE, GREEN, RED, INK = "#2864A0", "#C78025", "#287B68", "#B74848", "#273344"
METRICS = {
    "Ожидаемая продолжительность жизни": ("opzh", "лет"),
    "Младенческая смертность": ("inf_mort", "на 1 000 родившихся живыми"),
    "Смертность детей до пяти лет": ("under5_mort", "на 1 000 родившихся живыми"),
    "Материнская смертность": ("mat_mort", "на 100 000 родившихся живыми"),
    "Общий коэффициент смертности": ("cdr", "на 1 000 человек населения"),
    "Естественный прирост и убыль": ("nat_inc", "человек"),
}
SECTIONS = ["Введение", "Методология", "Россия", "Регионы", "Выводы", "Источники и данные"]

st.set_page_config(page_title="ЦУР 3 · Здоровье в России", page_icon=None, layout="wide")
st.markdown(
    """<style>
    .block-container {max-width: 1420px; padding-top: 2.2rem;}
    [data-testid="stMetric"] {background: #f2f5f8; padding: 1rem; border-radius: .4rem;}
    [data-testid="stMetricValue"] {font-size: 1.65rem;}
    h1 {letter-spacing: -.035em;} h2 {letter-spacing: -.02em;}
    </style>""", unsafe_allow_html=True,
)


@st.cache_data
def read_data():
    russia = pd.read_csv(DATA / "russia.csv")
    regions = pd.read_csv(DATA / "regions.csv")
    long = pd.read_csv(DATA / "long.csv")
    required = {
        "russia": {"year", "opzh", "opzh_m", "opzh_f", "inf_mort", "mat_mort", "mat_deaths", "births", "deaths", "nat_inc", "cdr", "gender_gap"},
        "regions": {"territory", "district", "type", "2015", "2019", "2021", "change_2015_2019", "change_2019_2021", "deviation_2021", "rank_2021", "outlier_2021"},
        "long": {"territory", "type", "district", "year", "code", "sex", "unit", "value", "preliminary", "change_abs", "growth_pct", "index_2015"},
    }
    for name, frame in (("russia", russia), ("regions", regions), ("long", long)):
        missing = required[name] - set(frame.columns)
        if missing:
            raise ValueError(f"В {name}.csv отсутствуют столбцы: {', '.join(sorted(missing))}")
    russia["year"] = pd.to_numeric(russia["year"], errors="raise").astype(int)
    long["year"] = pd.to_numeric(long["year"], errors="raise").astype(int)
    long["preliminary"] = long["preliminary"].astype(str).str.lower().isin(["true", "1"])
    if "under5_mort" not in russia.columns:
        russia["under5_mort"] = np.nan
    for column in (required["russia"] - {"year"}) | {"under5_mort"}:
        russia[column] = pd.to_numeric(russia[column], errors="raise")
    for column in ["2015", "2019", "2021", "change_2015_2019", "change_2019_2021", "deviation_2021", "rank_2021"]:
        regions[column] = pd.to_numeric(regions[column], errors="raise")
    return russia.sort_values("year"), regions, long


def number(value, decimals=2):
    if pd.isna(value):
        return "нет данных"
    return f"{value:,.{decimals}f}".replace(",", " ").replace(".", ",")


def layout(fig, title, ytitle=None, height=430):
    fig.update_layout(
        title=dict(text=title, font=dict(size=20)), height=height,
        font=dict(family="Arial, sans-serif", color=INK, size=13),
        paper_bgcolor="white", plot_bgcolor="white",
        margin=dict(l=30, r=30, t=70, b=50),
        legend=dict(orientation="h", y=-0.18, x=0), hovermode="closest",
    )
    fig.update_xaxes(showgrid=False, automargin=True)
    fig.update_yaxes(gridcolor="#e4e9ef", zerolinecolor="#bac5d0", automargin=True, title=ytitle)
    return fig


def chart(fig, key):
    kwargs = dict(key=key, config={"displaylogo": False, "scrollZoom": False}, theme=None)
    if "width" in inspect.signature(st.plotly_chart).parameters:
        kwargs["width"] = "stretch"
    else:
        kwargs["use_container_width"] = True
    st.plotly_chart(fig, **kwargs)


def downloadable(frame, name, key):
    st.download_button(
        "Скачать выбранные данные (CSV)", frame.to_csv(index=False).encode("utf-8-sig"),
        file_name=name, mime="text/csv", key=key,
    )


def point(frame, year, column):
    values = frame.loc[frame.year == year, column]
    return values.iloc[0] if not values.empty else np.nan


def table(frame, **kwargs):
    sizing = {"width": "stretch"} if "width" in inspect.signature(st.dataframe).parameters else {"use_container_width": True}
    st.dataframe(frame, hide_index=True, **sizing, **kwargs)


try:
    rf, regional, tidy = read_data()
except (OSError, ValueError) as exc:
    st.error(f"Не удалось открыть подготовленные данные: {exc}")
    st.stop()

subjects = regional[regional["type"] == "region"].copy()
country = regional[regional["type"] == "country"]
district_rows = regional[regional["type"] == "district"]
year_min, year_max = int(rf["year"].min()), int(rf["year"].max())

with st.sidebar:
    st.title("ЦУР 3")
    st.caption("Хорошее здоровье и благополучие")
    page = st.radio("Раздел", SECTIONS, index=0)
    st.divider()
    years = st.slider("Период наблюдений", year_min, year_max, (year_min, year_max))
    metric_label = st.selectbox("Показатель", list(METRICS))
    st.caption("Период и показатель управляют динамикой России. Региональные сравнения доступны по ОПЖ.")
    st.subheader("Сравнение регионов")
    district_options = sorted(subjects["district"].dropna().unique().tolist())
    district = st.selectbox("Федеральный округ", ["Все округа"] + district_options)
    eligible = subjects if district == "Все округа" else subjects[subjects["district"] == district]
    available_names = sorted(eligible["territory"].tolist())
    # После смены округа ранее выбранные территории должны оставаться допустимыми.
    if "selected_regions" in st.session_state:
        st.session_state["selected_regions"] = [n for n in st.session_state["selected_regions"] if n in available_names]
    selected_names = st.multiselect("Территории", available_names, key="selected_regions")
    st.caption("Пустой выбор означает все территории выбранного округа.")
    st.divider()
    st.caption("Зейда А.В. · Капустник К.А.\n\nББИ-24-БА1\n\nАнализ данных на Python")

metric, unit = METRICS[metric_label]
period_rf = rf[rf["year"].between(*years)].copy()
region_view = eligible[eligible["territory"].isin(selected_names)] if selected_names else eligible.copy()
anchors = [y for y in [2015, 2019, 2021] if years[0] <= y <= years[1]]

st.title("Здоровье в России: восстановление и различия между регионами")
st.caption("ЦУР 3 · Россия, 2015–2024 · Региональный срез, 2015 / 2019 / 2021")

if page == "Введение":
    st.header("Что изменилось за десять лет")
    st.write(
        "ЦУР 3 объединяет задачи сохранения здоровья и снижения предотвратимой смертности. "
        "Мы проверяем, как изменились показатели России и насколько различается ожидаемая "
        "продолжительность жизни в регионах. Главный вопрос: восстановился ли показатель "
        "после снижения 2020–2021 годов и какой разрыв остается до национальной цели?"
    )
    c1, c2, c3 = st.columns(3)
    opzh_prelim=tidy[(tidy.type=='country')&(tidy.year==2024)&(tidy.code=='opzh')].preliminary.any()
    infant_prelim=tidy[(tidy.type=='country')&(tidy.year==2024)&(tidy.code=='inf_mort')].preliminary.any()
    c1.metric("ОПЖ России, 2024"+(" (предв.)" if opzh_prelim else ""), f"{number(point(rf,2024,'opzh'))} года")
    c2.metric("Младенческая смертность, 2024"+(" (предв.)" if infant_prelim else ""), f"{number(point(rf,2024,'inf_mort'), 1)} на 1 000")
    c3.metric("Разрыв ОПЖ территорий, 2021", f"{number(subjects['2021'].max() - subjects['2021'].min())} года")
    st.write(
        f"В проверенном ряду ОПЖ составила {number(point(rf,2015,'opzh'))} года в 2015-м, "
        f"{number(point(rf,2019,'opzh'))} в 2019-м, {number(point(rf,2021,'opzh'))} в 2021-м "
        f"и {number(point(rf,2023,'opzh'))} в 2023-м. Значение 2024 года — "
        f"{number(point(rf,2024,'opzh'))}. Младенческая смертность в 2020 и 2021 годах "
        f"составляла соответственно {number(point(rf,2020,'inf_mort'),1)} и "
        f"{number(point(rf,2021,'inf_mort'),1)} на 1 000 живорождений."
    )
    st.info(
        "ОПЖ — условная ожидаемая продолжительность жизни при рождении при сохранении "
        "возрастной смертности соответствующего года. Она не равна среднему возрасту умерших."
    )
    st.write(
        "В разделе «Россия» можно выбрать показатель и период. В «Регионах» — "
        "округ и территории, доступный опорный год и точки на диаграмме. "
        "Все графики показывают значения при наведении; выбранные таблицы можно скачать."
    )
    st.caption("Выполнили: Зейда А.В. и Капустник К.А., группа ББИ-24-БА1.")

elif page == "Методология":
    st.header("Как устроены данные")
    st.write(
        "Основа работы — переданная сводка показателей Росстата, сверенная и дополненная "
        "официальными публикациями. Ряд ОПЖ обновлен из единой таблицы ЕМИСС № 31293. "
        "Общероссийские ряды содержат десять лет, региональная таблица — три опорных года. "
        "Исходные значения сохранены в папке data/raw. Обработанные таблицы отделены от них."
    )
    table(pd.DataFrame([
        ["ОПЖ при рождении", "лет", "Интегральная характеристика смертности; национальная цель"],
        ["Младенческая смертность", "на 1 000 живорождений", "Смерти до года; показатель, связанный с задачей 3.2"],
        ["Смертность детей до пяти лет", "на 1 000 живорождений", "Вероятность смерти до пяти лет; индикатор ЦУР 3.2.1"],
        ["Материнская смертность", "на 100 000 живорождений", "Задача 3.1, индикатор 3.1.1; без поздней материнской смерти"],
        ["Общий коэффициент смертности", "на 1 000 населения", "Демографический контекст; зависит от возрастного состава"],
        ["Естественный прирост / убыль", "человек", "Число родившихся минус число умерших; миграция не учитывается"],
    ], columns=["Показатель", "Единица", "Определение и связь с ЦУР"]))
    st.write(
        "Младенческую смертность нельзя отождествлять с международным индикатором 3.2.2: "
        "он измеряет неонатальную смертность в первые 28 дней жизни. ОПЖ, общая смертность "
        "и естественная убыль также не дают полной оценки достижения всех задач ЦУР 3."
    )
    st.subheader("Подготовка и проверки")
    st.write(
        "Числа с десятичной запятой и пробелами приведены к числовому типу. Годы — к целым "
        "числам, признаки предварительных значений сохранены. Пропуски не заменялись нулями "
        "или интерполяцией. Рассчитаны абсолютные изменения, проценты, индекс к 2015 году, "
        "разрыв женщин и мужчин, отклонения от России и ранги территорий."
    )
    birth_difference = (rf.births - rf.deaths - rf.nat_inc).abs()
    maternal_difference = (rf.mat_deaths / rf.births * 100000 - rf.mat_mort).abs().dropna()
    table(pd.DataFrame([
        ["Родившиеся − умершие = естественный прирост", f"Максимальное расхождение: {number(birth_difference.max(), 0)} человек"],
        ["Умершие матери / родившиеся × 100 000", f"Максимальное расхождение: {number(maternal_difference.max(), 3)}; допуск 0,1"],
        ["Ключ территории × год × показатель × пол", f"Дубликатов: {tidy.duplicated(['territory','year','code','sex']).sum()}"],
        ["Неопубликованные / отсутствующие значения", f"Пропусков в длинной таблице: {tidy.value.isna().sum()}"],
    ], columns=["Проверка", "Результат"]))
    st.write(
        "Архангельская и Тюменская области представлены без автономных округов, а округа — "
        "отдельно. Это устраняет перекрытие территорий. Региональные значения "
        "сверены с официальными публикациями и обновлены из ЕМИСС. Значения ОПЖ "
        "не суммируются. Общероссийское и окружные значения берутся из "
        "официальных агрегированных рядов, а не из среднего по территориям."
    )
    st.subheader("Ограничения")
    st.write(
        "Росстат пересчитывает демографические показатели с учетом переписи. В итоговом "
        "наборе Россия и территории по ОПЖ приведены к одной версии ЕМИСС; различия "
        "с первоначальными материалами отражены в журнале исправлений. Часть значений "
        "2024 года имеет предварительный характер; это отмечено рядом с наблюдениями. "
        "Пропуски сохранены и видны в таблицах. Региональный анализ ограничен тремя "
        "опорными годами."
    )
    st.write(
        "Состав федеральных округов менялся: Крым и Севастополь вошли в ЮФО в 2016 году, "
        "Бурятия и Забайкальский край — в ДФО в 2018-м. В выгрузке использованы современные коды округов с историческими значениями для того же состава. Основная диаграмма сравнивает округа "
        "для 2019 и 2021 годов. Корреляция и IQR описывают переданные наблюдения; они "
        "не доказывают причины изменений. Прохождение арифметических проверок само по себе "
        "не подтверждает достоверность каждого исходного числа."
    )

elif page == "Россия":
    st.header(f"{metric_label}: {years[0]}–{years[1]}")
    st.caption("Территория: Российская Федерация. Выбор округа и территорий применяется в разделе «Регионы».")
    observed = period_rf.dropna(subset=[metric])
    if observed.empty:
        st.info("Для выбранного показателя и периода нет опубликованных значений в этом наборе.")
    else:
        first, last = observed.iloc[0], observed.iloc[-1]
        divisor = 1000 if metric == "nat_inc" else 1
        display_unit = "тыс. человек" if metric == "nat_inc" else unit
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Последнее значение, {int(last.year)}", f"{number(last[metric]/divisor)}")
        c2.metric(f"Изменение {int(first.year)} → {int(last.year)}", f"{number((last[metric]-first[metric])/divisor)}")
        if first[metric] > 0 and metric != "nat_inc":
            c3.metric("Изменение к первому году", f"{number((last[metric]/first[metric]-1)*100,1)} %")
        else:
            c3.metric("Наблюдений", str(len(observed)))
        st.caption(f"Единица значений и абсолютного изменения: {display_unit}. Проценты не рассчитываются для знакопеременного естественного прироста.")
        preliminary = tidy[(tidy.type == "country") & (tidy.code == metric) & (tidy.value.notna()) & tidy.preliminary]
        preliminary_years = set(preliminary.year)
        fig = go.Figure()
        values = period_rf[metric] / divisor
        custom = [["предварительные / текущий учет" if y in preliminary_years else "исходная опубликованная версия"] for y in period_rf.year]
        if metric == "opzh":
            fig.add_trace(go.Scatter(x=period_rf.year, y=values, mode="lines+markers", name="Россия", connectgaps=True,
                marker=dict(color=BLUE, size=8), line=dict(color=BLUE, width=3), customdata=custom,
                hovertemplate="%{x}: %{y:.2f} лет<br>%{customdata[0]}<extra></extra>"))
            prelim = period_rf[period_rf.year.isin(preliminary_years)]
            fig.add_trace(go.Scatter(x=prelim.year, y=prelim[metric], mode="markers", marker=dict(symbol="circle-open",size=13,color=BLUE,line=dict(width=2)), name="Предварительные"))
            fig.add_hline(y=78, line_dash="dash", line_color=ORANGE, annotation_text="Национальная цель: 78 лет к 2030 году")
            if years[0] <= 2021 and years[1] >= 2020:
                fig.add_vrect(x0=max(years[0]-.2,2019.5),x1=min(years[1]+.2,2021.5),fillcolor="#e8edf3",opacity=.45,line_width=0,layer="below")
        else:
            colors = [GREEN if v >= 0 else RED for v in values] if metric == "nat_inc" else [RED if metric == "mat_mort" and y == 2021 else BLUE for y in period_rf.year]
            fig.add_trace(go.Bar(x=period_rf.year,y=values,marker_color=colors,name=metric_label,customdata=custom,
                hovertemplate="%{x}: %{y:,.2f}<br>%{customdata[0]}<extra></extra>"))
        fig.update_xaxes(dtick=1)
        chart(layout(fig, metric_label, display_unit), "national_main")
        if metric == "opzh":
            available = period_rf.dropna(subset=["opzh_m","opzh_f"])
            if not available.empty:
                gender = go.Figure()
                for col,label,color in [("opzh_m","Мужчины",BLUE),("opzh_f","Женщины",ORANGE)]:
                    gender.add_trace(go.Scatter(x=period_rf.year,y=period_rf[col],mode="lines+markers",name=label,connectgaps=True,line=dict(color=color,width=2.5),hovertemplate="%{x}: %{y:.2f} лет<extra>%{fullData.name}</extra>"))
                gender.update_xaxes(dtick=1)
                chart(layout(gender,"ОПЖ мужчин и женщин", "лет"),"national_gender")
                row = available.iloc[-1]
                st.write(f"В {int(row.year)} году разрыв женщин и мужчин — {number(row.gender_gap)} года. Этот набор не содержит возрастных коэффициентов смертности, необходимых для объяснения разрыва.")
            else:
                st.info("В выбранном периоде нет ОПЖ по полу; значения не восстановлены расчетом.")
            gap = 78-last.opzh
            yearly = gap/(2030-int(last.year))
            st.write(f"От значения {int(last.year)} года до 78 лет остается {number(gap)} года. Линейный расчет требует {number(yearly)} года ежегодно до 2030-го. Это арифметический сценарий, а не прогноз.")
        elif metric == "inf_mort":
            st.write(f"Для выбранного периода сравниваются фактически имеющиеся наблюдения {int(first.year)} и {int(last.year)} годов. В 2020–2021 значения составили {number(point(rf,2020,'inf_mort'),1)} → {number(point(rf,2021,'inf_mort'),1)} на 1 000 живорождений. Причины изменений по этой таблице установить нельзя.")
        elif metric == "under5_mort":
            st.write("Этот показатель соответствует международному индикатору ЦУР 3.2.1. Его нельзя заменять младенческой или неонатальной смертностью: возрастные границы отличаются. Для отсутствующих годов значения не интерполируются.")
        elif metric == "mat_mort":
            peak_row=rf.dropna(subset=['mat_mort']).loc[rf.mat_mort.idxmax()]
            st.write(f"Максимум полного ряда — {number(peak_row.mat_mort,1)} в {int(peak_row.year)} году. В выбранном периоде последнее наблюдение — {number(last.mat_mort,1)} в {int(last.year)} году. Коэффициент зависит и от числа умерших матерей, и от числа родившихся.")
        elif metric == "nat_inc":
            low_row=rf.loc[rf.nat_inc.idxmin()]
            st.write(f"Естественная убыль — разница числа родившихся и умерших. Она не учитывает миграцию. Минимальное значение полного ряда — {number(low_row.nat_inc,0)} человек в {int(low_row.year)} году.")
        else:
            baseline=rf.loc[rf.year==2019,"cdr"].iloc[0]
            peak=rf.loc[rf.year==2021,"cdr"].iloc[0]
            st.write(f"В 2019–2021 общий коэффициент смертности вырос с {number(baseline,1)} до {number(peak,1)} на 1 000 населения. Его изменение отражает и смертность, и возрастную структуру; это не стандартизованный по возрасту показатель.")
        table(observed[["year",metric]].rename(columns={"year":"Год",metric:metric_label}))
        downloadable(observed[["year",metric]],f"russia_{metric}_{years[0]}_{years[1]}.csv","national_download")

elif page == "Регионы":
    st.header("Региональные различия ОПЖ")
    st.caption("Региональные фильтры: округ и территории. В переданном наборе региональные значения есть только для ОПЖ.")
    if metric != "opzh":
        st.info(f"Региональных значений показателя «{metric_label}» в наборе нет. Ниже доступен отдельный региональный анализ ОПЖ.")
    if not anchors:
        st.info("В выбранном периоде нет опорных региональных лет. Доступные годы: 2015, 2019, 2021. Между ними значения не интерполируются.")
    elif region_view.empty:
        st.info("Выбранные региональные фильтры не оставили территорий для сравнения.")
    else:
        snapshot = st.selectbox("Опорный год",anchors,index=len(anchors)-1)
        col = str(snapshot)
        valid = region_view.dropna(subset=[col]).copy()
        nationwide = subjects.dropna(subset=[col]).copy()
        nationwide["selected_year_rank"] = nationwide[col].rank(ascending=False,method="min").astype(int)
        q1,q3=nationwide[col].quantile([.25,.75])
        iqr=q3-q1
        low,high=q1-1.5*iqr,q3+1.5*iqr
        nationwide['selected_year_outlier']=(nationwide[col]<low)|(nationwide[col]>high)
        valid = valid.merge(nationwide[["territory","selected_year_rank","selected_year_outlier"]],on="territory",how="left")
        rf_year = float(rf.loc[rf.year == snapshot,"opzh"].iloc[0])
        c1,c2,c3 = st.columns(3)
        c1.metric("Территорий с данными",f"{len(valid)} из {len(region_view)}")
        c2.metric(f"Россия, {snapshot}",number(rf_year))
        c3.metric("Размах выбранных территорий",number(valid[col].max()-valid[col].min()) if len(valid) else "нет данных")
        st.caption("ОПЖ и размах выражены в годах. Ранг рассчитывается по всем территориям с данными за выбранный год; фильтр его не меняет.")
        if valid.empty:
            st.info("Для выбранных территорий нет значений ОПЖ за этот год.")
        else:
            st.subheader("Распределение и место территории")
            histogram = go.Figure(go.Histogram(x=valid[col],nbinsx=15,marker_color=BLUE,
                hovertemplate="ОПЖ: %{x}<br>Территорий: %{y}<extra></extra>"))
            histogram.add_vline(x=rf_year,line_dash="dash",line_color=ORANGE,annotation_text=f"Россия: {number(rf_year)}")
            histogram.update_xaxes(title="ОПЖ, лет")
            chart(layout(histogram,f"Распределение ОПЖ, {snapshot}","число территорий",360),"regional_histogram")
            st.caption(f"По всем {len(nationwide)} территориям этого года: Q1 = {number(q1)}, Q3 = {number(q3)}; границы 1,5 IQR: {number(low)}–{number(high)}. За границами {int(nationwide.selected_year_outlier.sum())} наблюдений. Такой флаг описывает край распределения и не означает ошибку данных.")
            order=st.selectbox("Порядок рейтинга",["Наибольшие значения","Наименьшие значения"])
            limit = st.slider("Территорий на диаграмме рейтинга",1,min(85,len(valid)),min(20,len(valid))) if len(valid)>1 else 1
            ranked = valid.sort_values([col,"territory"],ascending=[order=="Наименьшие значения",True]).head(limit).sort_values(col)
            ranking = go.Figure(go.Bar(x=ranked[col],y=ranked.territory,orientation="h",marker_color=[GREEN if v>=rf_year else BLUE for v in ranked[col]],customdata=ranked[["selected_year_rank","district"]].values,
                hovertemplate="%{y}<br>ОПЖ: %{x:.2f} лет<br>Ранг в стране: %{customdata[0]}<br>Округ: %{customdata[1]}<extra></extra>"))
            ranking.add_vline(x=rf_year,line_dash="dash",line_color=ORANGE)
            chart(layout(ranking,f"{order} в выбранной группе, {snapshot}",height=max(380,limit*30+100)),"regional_rank")
            st.caption("Шкала столбцов начинается с нуля. Равным значениям присваивается одинаковый минимальный ранг.")
            detail = valid.copy()
            if 2019 in anchors and 2021 in anchors:
                st.subheader("Изменение 2019–2021 и выбор точек")
                paired = region_view.dropna(subset=["2019","2021"]).copy()
                association = paired["2019"].corr(paired["change_2019_2021"]) if len(paired)>2 else np.nan
                scatter = go.Figure()
                palette = [BLUE,GREEN,ORANGE,RED,"#786CB0","#60808B","#B47B72","#588359"]
                for i,(district_name,block) in enumerate(paired.groupby("district",sort=True)):
                    scatter.add_trace(go.Scatter(x=block["2019"],y=block["change_2019_2021"],mode="markers",name=str(district_name),
                        marker=dict(size=9,color=palette[i%len(palette)],opacity=.82),customdata=block[["territory","2021"]].values,
                        hovertemplate="%{customdata[0]}<br>2019: %{x:.2f} лет<br>2021: %{customdata[1]:.2f} лет<br>Изменение: %{y:.2f} года<extra></extra>"))
                scatter.update_xaxes(title="ОПЖ в 2019 году, лет")
                scatter.update_layout(clickmode="event+select",dragmode="select")
                layout(scatter,"Исходный уровень и изменение ОПЖ", "изменение 2019 → 2021, лет",470)
                if "on_select" in inspect.signature(st.plotly_chart).parameters:
                    if st.button("Сбросить выбор точек",key="reset_plot_selection"):
                        st.session_state['selection_generation']=st.session_state.get('selection_generation',0)+1
                    kwargs = {"width":"stretch"} if "width" in inspect.signature(st.plotly_chart).parameters else {"use_container_width":True}
                    event = st.plotly_chart(scatter,key=f"regional_selection_{district}_{','.join(selected_names)}_{st.session_state.get('selection_generation',0)}",on_select="rerun",selection_mode=("points","box","lasso"),theme=None,config={"displaylogo":False},**kwargs)
                    points = event.get("selection",{}).get("points",[]) if event else []
                    clicked = []
                    for point in points:
                        values = point.get("customdata",[])
                        if values and values[0] in valid.territory.values:
                            clicked.append(values[0])
                    if clicked:
                        detail = valid[valid.territory.isin(clicked)].copy()
                        st.caption(f"Выбрано на диаграмме: {len(detail)}. Таблица и подробная динамика ниже показывают эти территории.")
                    else:
                        st.caption("Нажмите точку или выделите область: подробная динамика и таблица ниже отфильтруются. Для возврата ко всей группе используйте «Сбросить выбор точек».")
                else:
                    chart(scatter,"regional_scatter")
                    st.caption("В этой версии Streamlit выбор точек недоступен. Используйте список территорий слева.")
                st.write(f"Для текущей группы r Пирсона = {number(association)} (n = {len(paired)}). Корреляция описывает связь, а не причину. Начальное значение также входит в расчет изменения, что ограничивает интерпретацию.")
                fo = district_rows if district=="Все округа" else district_rows[district_rows.district==district]
                if not fo.empty:
                    dumbbell=go.Figure()
                    for _,row in fo.sort_values("2021").iterrows():
                        dumbbell.add_trace(go.Scatter(x=[row["2019"],row["2021"]],y=[row.district,row.district],mode="lines",connectgaps=True,line=dict(color="#bbc5d0",width=4),showlegend=False,hoverinfo="skip"))
                    for year,color in [("2019",BLUE),("2021",RED)]:
                        dumbbell.add_trace(go.Scatter(x=fo[year],y=fo.district,mode="markers",name=year,marker=dict(size=11,color=color),hovertemplate="%{y}: %{x:.2f} лет<extra>%{fullData.name}</extra>"))
                    dumbbell.update_xaxes(title="ОПЖ, лет")
                    chart(layout(dumbbell,"Федеральные округа: 2019 и 2021",height=390),"regional_fo")
            st.subheader("Подробная динамика выбранных территорий")
            if len(detail)>12:
                st.caption("Для читаемости на линии показаны 12 территорий с наибольшей ОПЖ выбранного года. Таблица содержит всю выбранную группу. Уточните список территорий, чтобы сравнить другие.")
            lines=go.Figure()
            for _,row in detail.sort_values(col,ascending=False).head(12).iterrows():
                lines.add_trace(go.Scatter(x=anchors,y=[row[str(y)] for y in anchors],mode="lines+markers",name=row.territory,connectgaps=True,
                    hovertemplate="%{x}: %{y:.2f} лет<extra>%{fullData.name}</extra>"))
            lines.add_trace(go.Scatter(x=anchors,y=[float(rf.loc[rf.year==y,"opzh"].iloc[0]) for y in anchors],mode="lines+markers",name="Россия",connectgaps=True,line=dict(color=INK,dash="dash",width=3)))
            lines.update_xaxes(tickvals=anchors)
            chart(layout(lines,"Опорные значения ОПЖ", "лет",520),"regional_detail")
            st.caption("Линии соединяют только имеющиеся опорные наблюдения. Они не показывают значения промежуточных лет.")
            detail_table=detail[["territory","district",col,"selected_year_rank","selected_year_outlier"]].copy()
            detail_table["Отклонение от России, лет"]=(detail_table[col]-rf_year).round(2)
            detail_table=detail_table.rename(columns={"territory":"Территория","district":"Округ",col:f"ОПЖ {snapshot}, лет","selected_year_rank":"Ранг в стране","selected_year_outlier":"За границами 1,5 IQR"})
            table(detail_table.sort_values("Ранг в стране"))
            downloadable(detail,f"regional_opzh_{snapshot}.csv","regional_download")

elif page == "Выводы":
    st.header("Что подтверждают наблюдения")
    last_opzh=rf.dropna(subset=['opzh']).iloc[-1]
    target_gap=78-last_opzh.opzh
    yearly=target_gap/(2030-int(last_opzh.year))
    st.write(
        f"ОПЖ составила {number(point(rf,2021,'opzh'))} года в 2021-м, "
        f"{number(point(rf,2023,'opzh'))} в 2023-м и {number(last_opzh.opzh)} "
        f"в {int(last_opzh.year)} году. От последнего значения до цели 78 лет к 2030 году "
        f"остается {number(target_gap)} года. Линейный расчет дает {number(yearly)} года "
        f"ежегодно. Средний прирост 2015–2019 составлял "
        f"{number((point(rf,2019,'opzh')-point(rf,2015,'opzh'))/4)} года в год. "
        "Это сравнение темпов не является прогнозом выполнения цели."
    )
    infant_first=rf.dropna(subset=['inf_mort']).iloc[0]
    infant_last=rf.dropna(subset=['inf_mort']).iloc[-1]
    maternal_peak=rf.loc[rf.mat_mort.idxmax()]
    maternal_last=rf.dropna(subset=['mat_mort']).iloc[-1]
    st.write(
        f"Младенческая смертность: {number(infant_first.inf_mort,1)} в {int(infant_first.year)} "
        f"→ {number(infant_last.inf_mort,1)} в {int(infant_last.year)} на 1 000 живорождений. "
        f"Снижение — {number((1-infant_last.inf_mort/infant_first.inf_mort)*100,1)}%. "
        f"Материнская смертность: максимум {number(maternal_peak.mat_mort,1)} "
        f"в {int(maternal_peak.year)} году, последнее значение "
        f"{number(maternal_last.mat_mort,1)} в {int(maternal_last.year)}."
    )
    gap_row=rf.dropna(subset=['gender_gap']).iloc[-1]
    regional_valid=subjects.dropna(subset=['2021'])
    deviations=regional_valid['2021']-point(rf,2021,'opzh')
    lower=int((deviations<=-1).sum()); higher=int((deviations>=1).sum()); around=len(deviations)-lower-higher
    st.write(
        f"Разрыв ОПЖ женщин и мужчин в {int(gap_row.year)} году — {number(gap_row.gender_gap)} года. "
        f"Размах региональной ОПЖ в 2021-м — {number(regional_valid['2021'].max()-regional_valid['2021'].min())} года. "
        f"Из {len(regional_valid)} территорий {lower} отставали от России минимум на год, "
        f"{higher} превышали ее минимум на год, {around} находились в промежутке. "
        "Для объяснения различий нужны сведения о возрасте, причинах смерти, "
        "доступности помощи и качестве регистрации."
    )
    natural_last=rf.dropna(subset=['nat_inc']).iloc[-1]
    st.write(
        f"Естественный прирост / убыль: {number(natural_last.nat_inc,0)} человек "
        f"в {int(natural_last.year)} году. Это баланс родившихся и умерших, "
        "а не общий прирост населения с учетом миграции."
    )
    st.subheader("Что можно улучшить в следующем исследовании")
    st.write(
        "Для мониторинга цели нужен ежегодный региональный ряд одной версии публикации. "
        "Для объяснения динамики — возрастные коэффициенты и причины смерти. "
        "Смертность до пяти лет уже позволяет напрямую рассмотреть индикатор 3.2.1. "
        "Добавление неонатальной смертности расширит анализ международной задачи 3.2."
    )

elif page == "Источники и данные":
    st.header("Источники и границы проверки")
    st.write(
        "Автор исходной сводки — Капустник К.А. Переданные значения сверены с официальными "
        "источниками; исправления и версия выгрузки указаны в документации проекта. "
        "Исходная сводка сохранена отдельно от итоговых данных. Ниже указаны официальные "
        "публикации, использованные для проверки итогового набора."
    )
    st.markdown("[Росстат. Показатели ЦУР 3](https://rosstat.gov.ru/sdg/data/goal3)")
    labels = {"opzh":"ОПЖ России и территорий", "birthdeath":"Естественное движение населения 2015–2023", "birthdeath2024":"Естественное движение населения 2024", "infant":"Младенческая смертность 2015–2022", "infant2023":"Младенческая смертность 2023", "infant2024":"Младенческая смертность 2024", "maternal":"Материнская смертность", "maternalcount":"Число материнских смертей 2015–2022", "maternalcount2023":"Число материнских смертей 2023", "under5":"Смертность детей до пяти лет"}
    manifest_path = ROOT / "data" / "sources" / "source_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for source in manifest["sources"]:
            st.markdown(f"- [{labels.get(source['id'],source['id'])}]({source['source_url']}) — {source['locator']}")
        st.caption("Официальные выгрузки получены 07.10.2026. В проекте закреплён период 2015–2024.")
    st.markdown("[ООН. Определения показателей ЦУР](https://unstats.un.org/sdgs/metadata/)")
    st.write("Национальный ориентир: Указ Президента РФ от 07.05.2024 № 309 — 78 лет к 2030 году и 81 год к 2036 году.")
    st.subheader("Подготовленные таблицы")
    dataset = st.selectbox("Таблица",["Длинный формат","Россия по годам","Территории и округа"])
    view = {"Длинный формат":tidy,"Россия по годам":rf,"Территории и округа":regional}[dataset]
    st.caption(f"Размер: {len(view)} строк, {len(view.columns)} столбцов. Эта страница показывает полные подготовленные данные.")
    table(view)
    downloadable(view,{"Длинный формат":"long.csv","Россия по годам":"russia.csv","Территории и округа":"regions.csv"}[dataset],"all_data_download")

st.divider()
st.caption("Зейда А.В. · Капустник К.А. · ББИ-24-БА1 · Анализ данных на Python")
