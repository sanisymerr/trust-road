import React, { useMemo, useState } from 'react';

const productFacts = [
  { value: '5 000', label: 'целевой ориентир активных семей' },
  { value: '300+', label: 'платящих семей в первый год' },
  { value: '300 ₽', label: 'ежемесячная подписка freemium' },
  { value: '24–30 мес', label: 'ожидаемая окупаемость' },
];

const investorSignals = [
  'Семейный digital-продукт с понятной freemium-моделью',
  'Один продукт, три сценария коммуникации для разных аудиторий',
  'Геймификация решает реальную бытовую проблему, а не просто украшает интерфейс',
  'Подходит для App Store, Google Play, RuStore и партнёрских интеграций',
];

const modes = {
  parent: {
    id: 'parent',
    navLabel: 'Для родителей',
    chip: 'Семейный продукт',
    title: 'КидВест помогает детям делать дела без ссор, а семье — жить спокойнее.',
    subtitle:
      'Задачи, привычки, награды и понятный прогресс ребёнка — в одном приложении. Родитель видит результат, а ребёнок чувствует не давление, а игру и рост.',
    heroImage: '/assets/family-hero.svg',
    accent: 'parent',
    primaryCta: 'Запросить демо',
    secondaryCta: 'Смотреть возможности',
    aboutTitle: 'О продукте для семьи',
    aboutLead:
      'КидВест — семейное приложение-трекер задач для детей школьного возраста с элементами геймификации.',
    aboutText:
      'Родители задают ритм недели, назначают задания и награды, а ребёнок проходит ежедневные миссии в дружелюбной игровой логике. Это снижает количество конфликтов дома, делает прогресс прозрачным и помогает закреплять полезные привычки без чувства давления.',
    proof: [
      'Родительская и детская зоны внутри одного продукта',
      'Задачи, повторяющиеся дела, награды и история прогресса в одном интерфейсе',
      'Подходит для рутины дома, школы, режима и полезных привычек',
      'Геймификация встроена в поведение ребёнка, а не навешана поверх списка дел',
    ],
    benefitsTitle: 'Почему родители выбирают КидВест',
    benefitsText:
      'Продукт говорит на языке семьи: не контроль ради контроля, а спокойная система, которая помогает ребёнку включаться самостоятельно.',
    benefits: [
      {
        title: 'Меньше конфликтов',
        text: 'Ежедневные просьбы перестают быть бесконечными напоминаниями и превращаются в понятные семейные правила.',
      },
      {
        title: 'Понятный прогресс',
        text: 'Родитель видит, какие привычки закрепляются, а ребёнок понимает, за что получает награды и как двигается вперёд.',
      },
      {
        title: 'Мотивация вместо давления',
        text: 'Баллы, коллекции, магазин наград и недельные челленджи удерживают внимание сильнее обычного чек-листа.',
      },
      {
        title: 'Один цифровой центр семьи',
        text: 'Задачи, домашние обязанности, календарь и достижения собираются в одном современном сервисе.',
      },
    ],
    journeyTitle: 'Как КидВест работает в семье',
    journey: [
      {
        title: '1. Родитель собирает маршрут недели',
        text: 'Домашние дела, режим, уроки и маленькие семейные победы объединяются в один понятный сценарий.',
      },
      {
        title: '2. Ребёнок проходит задания как квест',
        text: 'Каждый шаг сопровождается визуальным прогрессом, монетами и ощущением, что он не “обязан”, а растёт.',
      },
      {
        title: '3. Семья видит реальный результат',
        text: 'Меньше споров, больше самостоятельности и прозрачная история достижений без ручных таблиц.',
      },
    ],
    galleryTitle: 'Как КидВест выглядит для семейной аудитории',
    galleryText:
      'На первом плане — доверие, комфорт и ощущение, что это качественный семейный сервис, которым приятно пользоваться каждый день.',
    spotlight: {
      title: 'Родительская панель управления',
      text: 'Крупные блоки, понятная иерархия, акцент на задачах недели, семейных наградах и визуальном спокойствии.',
      list: ['Постановка задач за 1–2 действия', 'Повторяющиеся сценарии без ручной рутины', 'Прогресс и история выполнения по каждому ребёнку'],
    },
    faq: [
      {
        q: 'Для какого возраста подходит КидВест?',
        a: 'Основное ядро продукта — дети 5–14 лет. Для каждой возрастной группы на сайте показана отдельная подача, чтобы ценность считывалась сразу.',
      },
      {
        q: 'Нужно ли родителю постоянно контролировать процесс?',
        a: 'Нет. Родитель задаёт систему, а продукт берёт на себя визуальную мотивацию, ритм и понятный сценарий наград.',
      },
      {
        q: 'Чем КидВест лучше обычного чек-листа?',
        a: 'Обычный список дел напоминает о задаче. КидВест делает выполнение эмоционально привлекательным за счёт героя, баллов, коллекций, наград и семейной логики.',
      },
    ],
    reviews: [
      {
        name: 'Анна Петрова',
        role: 'мама двоих детей',
        text: 'С КидВест домашние дела перестали быть полем битвы. Дети сами спрашивают, какие задания сегодня открыты и сколько монет можно заработать.',
      },
      {
        name: 'Олег Морозов',
        role: 'отец школьника',
        text: 'Мне нравится, что приложение выглядит как реальный продукт, а не как очередная таблица с обязанностями. Тут есть мотивация и спокойствие.',
      },
      {
        name: 'Елена Грачёва',
        role: 'руководитель семейного клуба',
        text: 'У проекта сильная идея для рынка: полезные привычки, вовлечение детей и понятная подписочная модель в одном решении.',
      },
    ],
    footerTitle: 'КидВест превращает ежедневные дела в спокойный семейный ритм и заметный прогресс ребёнка.',
    footerText:
      'Приложение объединяет родителя и ребёнка вокруг одной понятной системы: задачи, награды, рост, привычки и цифровой комфорт.',
  },
  kids: {
    id: 'kids',
    navLabel: 'Для детей',
    chip: 'Весёлые квесты',
    title: 'Выполняй задания, получай монеты, открывай героев и побеждай босса недели.',
    subtitle:
      'КидВест превращает уроки, порядок в комнате, режим и полезные привычки в яркие миссии, которые хочется проходить снова и снова.',
    heroImage: '/assets/kids-hero.svg',
    accent: 'kids',
    primaryCta: 'Хочу в КидВест',
    secondaryCta: 'Посмотреть квесты',
    aboutTitle: 'Твой игровой мир полезных дел',
    aboutLead: 'КидВест делает обычные задания похожими на настоящее приключение.',
    aboutText:
      'Каждый день ребёнок получает миссии, закрывает их, копит монеты и улучшает своего героя. За победы открываются новые награды, скины и приятные бонусы. Вместо скучного списка дел — яркий мир, где прогресс видно сразу.',
    proof: [
      'Яркие карточки заданий, понятные с первого взгляда',
      'Монеты, магазин наград и любимые персонажи',
      'Большие цели недели и эффект победы после каждого шага',
      'Приложение, которое хочется открыть самому, без напоминаний',
    ],
    benefitsTitle: 'Почему детям нравится КидВест',
    benefitsText:
      'Здесь нет скуки. Каждое полезное действие выглядит как маленькая победа, а день собирается в цепочку достижений.',
    benefits: [
      {
        title: 'Задания как миссии',
        text: 'Не просто “убери комнату”, а понятный квест с наградой, таймером и ощущением завершённого уровня.',
      },
      {
        title: 'Монеты и награды',
        text: 'Чем больше сделал, тем больше возможностей открыть: предметы, образы героя и семейные бонусы.',
      },
      {
        title: 'Босс недели',
        text: 'Каждая неделя заканчивается большой целью, которую особенно приятно закрывать и показывать родителям.',
      },
      {
        title: 'Твой персонаж',
        text: 'Герой развивается вместе с ребёнком, поэтому прогресс ощущается не в цифрах, а в любимом игровом мире.',
      },
    ],
    journeyTitle: 'Как ребёнок чувствует продукт',
    journey: [
      {
        title: '1. Вход в яркий мир',
        text: 'Первый экран сразу показывает задания, монеты, героя и большую цель дня — без скучных списков и мелкого текста.',
      },
      {
        title: '2. Каждое дело = новая победа',
        text: 'За выполненные задачи герой растёт, копилка пополняется, а прогресс ощущается эмоционально и визуально.',
      },
      {
        title: '3. Финал недели как мини-игра',
        text: 'Челленджи, награды и босс недели делают полезные привычки по-настоящему захватывающими.',
      },
    ],
    galleryTitle: 'Что ребёнок видит внутри КидВест',
    galleryText:
      'Крупные элементы, яркие цвета, понятные жесты и много эмоции — сайт сразу передаёт атмосферу приложения.',
    spotlight: {
      title: 'Экран магазина наград',
      text: 'Магазин визуализирует мотивацию: ребёнок не просто “закрывает задачу”, а понимает, ради чего старается и что сможет открыть дальше.',
      list: ['Карточки скинов и предметов', 'Монеты как видимая ценность', 'Большой эмоциональный отклик после каждой победы'],
    },
    faq: [
      {
        q: 'Это игра или полезное приложение?',
        a: 'По ощущениям — игра. По результату — приложение, которое помогает справляться с делами, режимом и полезными привычками.',
      },
      {
        q: 'А если задания надоедят?',
        a: 'Система квестов, наград и недельных целей постоянно поддерживает интерес, поэтому день не выглядит одинаковым.',
      },
      {
        q: 'Что можно получить за победы?',
        a: 'Монеты, новые образы героя, коллекционные награды и семейные бонусы, которые делают каждое достижение заметным.',
      },
    ],
    reviews: [
      {
        name: 'Илья',
        role: '9 лет',
        text: 'Мне понравилось, что это не похоже на уроки. Я закрываю задания и сразу хочу посмотреть, что откроется дальше.',
      },
      {
        name: 'Соня',
        role: '8 лет',
        text: 'Больше всего мне нравится магазин наград и герой. Из-за этого даже уборка кажется интереснее.',
      },
      {
        name: 'Катя',
        role: 'мама ребёнка из тестовой группы',
        text: 'Ребёнок начал сам вспоминать про задания, потому что ему стало интересно проходить их до конца.',
      },
    ],
    footerTitle: 'КидВест — мир, где полезные привычки становятся квестами, а каждый день приносит новую победу.',
    footerText:
      'Ребёнок играет, растёт и получает удовольствие от прогресса, а семья видит реальный результат в обычной жизни.',
  },
  teen: {
    id: 'teen',
    navLabel: 'Для подростков',
    chip: 'Стильный прогресс',
    title: 'Трекер задач и привычек, который выглядит современно и помогает реально держать ритм.',
    subtitle:
      'КидВест для подростков — это уже не просто “сделай дело”, а удобный цифровой инструмент для дисциплины, челленджей и личного роста.',
    heroImage: '/assets/teen-hero.svg',
    accent: 'teen',
    primaryCta: 'Получить ранний доступ',
    secondaryCta: 'Изучить функции',
    aboutTitle: 'Продукт для тех, кому важна самостоятельность',
    aboutLead:
      'Подростковая версия КидВест показывает не контроль, а личный маршрут прогресса.',
    aboutText:
      'Здесь задачи, привычки, серии выполнения и награды собраны в лаконичном интерфейсе с более взрослой подачей. Приложение помогает держать режим школы, спорта, домашних обязанностей и личных целей без ощущения, что тобой управляют.',
    proof: [
      'Более взрослый визуальный язык без инфантилизма',
      'Чёткие streak-механики и недельные вызовы',
      'Баланс между свободой пользователя и семейной системой',
      'Подготовка к взрослым digital-инструментам продуктивности',
    ],
    benefitsTitle: 'Почему подросткам это подходит',
    benefitsText:
      'В этой версии ценность строится вокруг контроля над собой, статуса и удобного инструмента, которым не стыдно пользоваться каждый день.',
    benefits: [
      {
        title: 'Самостоятельность',
        text: 'Приложение помогает самому видеть, как ты двигаешься по задачам, а не ждать напоминаний со стороны.',
      },
      {
        title: 'Серии и челленджи',
        text: 'Ежедневные и недельные streak-механики удерживают ритм и делают стабильность заметной.',
      },
      {
        title: 'Современный стиль',
        text: 'Интерфейс ощущается как технологичный сервис, а не как детское приложение для малышей.',
      },
      {
        title: 'Личный рост',
        text: 'КидВест помогает формировать дисциплину, привычки и организацию, которые пригодятся дальше в учёбе и жизни.',
      },
    ],
    journeyTitle: 'Как подросток видит ценность',
    journey: [
      {
        title: '1. Контроль над днём',
        text: 'Задачи, школа, тренировки и личные цели собираются в одном дашборде без лишнего шума.',
      },
      {
        title: '2. Видимый ритм',
        text: 'Серии выполнения, челленджи и графика прогресса мотивируют держать дисциплину каждый день.',
      },
      {
        title: '3. Продукт, которым не стыдно пользоваться',
        text: 'Более взрослый визуальный язык делает КидВест похожим на современный lifestyle-сервис, а не на детскую игрушку.',
      },
    ],
    galleryTitle: 'Как выглядит подростковая версия',
    galleryText:
      'Темнее, чище, технологичнее — визуальный тон показывает, что продукт уважает вкус аудитории и не упрощает всё до детского уровня.',
    spotlight: {
      title: 'Teen dashboard',
      text: 'Подростковая версия акцентирует ритм, результат и личный контроль — всё, что делает сервис полезным каждый день.',
      list: ['Серии и недельные челленджи', 'Лаконичная подача без инфантильности', 'Фокус на самостоятельности и личном росте'],
    },
    faq: [
      {
        q: 'Это не слишком по-детски?',
        a: 'Нет. Подростковая версия специально оформлена в более взрослом стиле с упором на прогресс, ритм и самостоятельность.',
      },
      {
        q: 'Зачем подростку такой трекер?',
        a: 'Чтобы держать под контролем школу, домашние задачи, тренировки и свои цели в одном удобном месте.',
      },
      {
        q: 'Можно ли настроить систему под себя?',
        a: 'Да. Логика продукта предполагает персонализацию задач, ритма недели, наград и уровней сложности.',
      },
    ],
    reviews: [
      {
        name: 'Никита',
        role: '13 лет',
        text: 'Мне зашло, что это выглядит как нормальный современный сервис. Хочется пользоваться, а не закрыть через минуту.',
      },
      {
        name: 'Алина',
        role: '12 лет',
        text: 'Я бы вела там школу, тренировки и свои цели, потому что интерфейс понятный и не выглядит детским.',
      },
      {
        name: 'Елена Л.',
        role: 'мама подростка',
        text: 'Для меня важно, что подростковая версия не выглядит как приложение для малышей. Это сразу повышает шанс реального использования.',
      },
    ],
    footerTitle: 'КидВест — современный teen-friendly инструмент, который помогает подростку держать ритм и видеть свой рост.',
    footerText:
      'Продукт даёт баланс между свободой, понятной системой и визуальным ощущением, что ты пользуешься действительно классным сервисом.',
  },
};

const navItems = [
  { id: 'about', label: 'О продукте' },
  { id: 'benefits', label: 'Преимущества' },
  { id: 'journey', label: 'Сценарий' },
  { id: 'showcase', label: 'Галерея' },
  { id: 'faq', label: 'FAQ' },
  { id: 'reviews', label: 'Отзывы' },
];

function SectionTitle({ chip, title, lead, text, align = 'left' }) {
  return (
    <div className={`section-heading ${align === 'center' ? 'center' : ''}`}>
      <span className="eyebrow">{chip}</span>
      <h2>{title}</h2>
      {lead ? <p className="lead">{lead}</p> : null}
      {text ? <p>{text}</p> : null}
    </div>
  );
}

function App() {
  const [mode, setMode] = useState('parent');
  const [openFaq, setOpenFaq] = useState(0);
  const current = useMemo(() => modes[mode], [mode]);

  return (
    <div className={`page theme-${current.accent}`}>
      <div className="ambient ambient-1" />
      <div className="ambient ambient-2" />
      <div className="ambient ambient-3" />

      <header className="site-header">
        <div className="container header-inner">
          <a className="logo" href="#top" aria-label="КидВест">
            <img src="/assets/logo-kidquest.svg" alt="КидВест" />
          </a>

          <nav className="main-nav">
            {navItems.map((item) => (
              <a key={item.id} href={`#${item.id}`}>{item.label}</a>
            ))}
          </nav>

          <a className="header-cta" href="#footer-cta">Связаться</a>
        </div>
      </header>

      <main id="top">
        <section className="hero container">
          <div className="hero-copy glass-card">
            <span className="eyebrow">{current.chip}</span>
            <h1>{current.title}</h1>
            <p className="hero-subtitle">{current.subtitle}</p>

            <div className="mode-switcher" role="tablist" aria-label="Аудитории КидВест">
              {Object.values(modes).map((item) => (
                <button
                  key={item.id}
                  className={item.id === mode ? 'active' : ''}
                  onClick={() => {
                    setMode(item.id);
                    setOpenFaq(0);
                  }}
                  role="tab"
                  aria-selected={item.id === mode}
                >
                  {item.navLabel}
                </button>
              ))}
            </div>

            <div className="hero-actions">
              <a className="btn btn-primary" href="#footer-cta">{current.primaryCta}</a>
              <a className="btn btn-secondary" href="#about">{current.secondaryCta}</a>
            </div>

            <div className="contact-line">
              <span>hello@kidquest-demo.ru</span>
              <span>Telegram: @kidquest_demo</span>
              <span>Demo-call: +7 (900) 000-00-00</span>
            </div>
          </div>

          <div className="hero-visual">
            <div className="hero-frame glass-card">
              <img className="hero-illustration" src={current.heroImage} alt={current.navLabel} />
            </div>

            <div className="floating-stats glass-card">
              {productFacts.map((metric) => (
                <div key={metric.label}>
                  <strong>{metric.value}</strong>
                  <span>{metric.label}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="ticker-shell container">
          <div className="ticker glass-card">
            {investorSignals.map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>
        </section>

        <section id="about" className="section container">
          <div className="two-col intro-layout">
            <div>
              <SectionTitle chip="О продукте" title={current.aboutTitle} lead={current.aboutLead} text={current.aboutText} />
            </div>
            <aside className="glass-card proof-card">
              <div className="proof-card-head">
                <span className="eyebrow small">Что получает аудитория</span>
                <h3>Ключевая ценность на одном экране</h3>
              </div>
              <ul>
                {current.proof.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </aside>
          </div>
        </section>

        <section className="section container product-platform">
          <SectionTitle
            chip="Платформа"
            title="Один продукт — три сильных сценария коммуникации"
            text="На защите это работает особенно хорошо: вы показываете не просто красивый сайт, а зрелый digital-продукт с разными точками входа для семьи, ребёнка и подростка."
            align="center"
          />
          <div className="platform-grid">
            <article className="glass-card platform-card highlight-card">
              <span className="eyebrow small">Почему это сильно</span>
              <h3>Сайт сразу демонстрирует продуктовую зрелость</h3>
              <p>
                Вместо одного шаблонного сервиса КидВест показывает сегментированную подачу — это усиливает восприятие проекта как реального стартапа, а не учебного макета.
              </p>
            </article>
            <article className="glass-card platform-card stat-card">
              <strong>Freemium + подписка</strong>
              <p>Понятная модель монетизации: базовый доступ, премиальные сценарии, развитие семейного профиля и расширенные награды.</p>
            </article>
            <article className="glass-card platform-card stat-card">
              <strong>Семейная retention-логика</strong>
              <p>Чем больше ребёнок включается в повседневные ритуалы, тем выше ценность для всей семьи и устойчивость использования.</p>
            </article>
          </div>
        </section>

        <section id="benefits" className="section container">
          <SectionTitle chip="Преимущества" title={current.benefitsTitle} text={current.benefitsText} />
          <div className="benefit-grid">
            {current.benefits.map((benefit, idx) => (
              <article className="benefit-card glass-card" key={benefit.title}>
                <div className="benefit-index">0{idx + 1}</div>
                <h3>{benefit.title}</h3>
                <p>{benefit.text}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="journey" className="section container journey-section">
          <SectionTitle chip="Сценарий" title={current.journeyTitle} text="Эта часть делает презентацию живой: не просто список функций, а путь пользователя внутри продукта." />
          <div className="journey-grid">
            {current.journey.map((step) => (
              <article className="glass-card journey-card" key={step.title}>
                <h3>{step.title}</h3>
                <p>{step.text}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="showcase" className="section container media-section">
          <SectionTitle chip="Галерея" title={current.galleryTitle} text={current.galleryText} />

          <div className="showcase-shell glass-card">
            <div className="showcase-topbar">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
              <span className="tab-label">KidQuest Product Preview</span>
            </div>

            <div className="media-grid">
              <figure className="glass-card media-card tall">
                <img src="/assets/presentation-hero.png" alt="Главный визуал презентации КидВест" />
                <figcaption>Эмоциональный образ продукта для семьи и ребёнка</figcaption>
              </figure>

              <figure className="glass-card media-card tall">
                <img src="/assets/presentation-mockup.png" alt="Игровой интерфейс КидВест" />
                <figcaption>Геймификация, магазин наград и визуальный прогресс</figcaption>
              </figure>

              <div className="glass-card media-card spotlight-card">
                <span className="eyebrow small">Фокус экрана</span>
                <h3>{current.spotlight.title}</h3>
                <p>{current.spotlight.text}</p>
                <ul>
                  {current.spotlight.list.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>

              <div className="glass-card media-card video-card">
                <video controls poster="/assets/presentation-mockup.png">
                  <source src="/assets/kidquest-demo.mp4" type="video/mp4" />
                </video>
                <div className="video-copy">
                  <span className="eyebrow small">Demo video</span>
                  <h3>Короткая демонстрация продукта</h3>
                  <p>
                    Видео усиливает эффект живой презентации: на защите можно быстро показать атмосферу продукта без переключения в сторонние материалы.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="section container metrics-section">
          <SectionTitle
            chip="Ценность проекта"
            title="Почему этот продукт выглядит убедительно на защите"
            text="Команда показывает не только дизайн экранов, но и зрелую логику: сегментация аудитории, понятная монетизация, продуктовый маршрут и визуальная система, которую можно масштабировать дальше."
            align="center"
          />
          <div className="metrics-grid">
            {productFacts.map((item) => (
              <article className="glass-card metric-card" key={item.label}>
                <strong>{item.value}</strong>
                <span>{item.label}</span>
              </article>
            ))}
          </div>
        </section>

        <section id="faq" className="section container">
          <SectionTitle chip="FAQ" title="Вопросы и ответы" text="Короткие ответы помогают быстро снять возражения и показать продукт зрелым уже на первом просмотре." />
          <div className="faq-list glass-card">
            {current.faq.map((item, idx) => {
              const open = openFaq === idx;
              return (
                <button key={item.q} className={`faq-item ${open ? 'open' : ''}`} onClick={() => setOpenFaq(open ? -1 : idx)}>
                  <div>
                    <strong>{item.q}</strong>
                    <p>{item.a}</p>
                  </div>
                  <span>{open ? '−' : '+'}</span>
                </button>
              );
            })}
          </div>
        </section>

        <section id="reviews" className="section container">
          <SectionTitle chip="Отзывы" title="Что говорят о КидВест" text="Семьи отмечают, что КидВест помогает сократить количество напоминаний, делает выполнение задач понятнее для ребёнка и превращает рутину в систему маленьких достижений." />
          <div className="review-grid">
            {current.reviews.map((review) => (
              <article className="glass-card review-card" key={review.name + review.role}>
                <div className="review-head">
                  <div className="avatar">{review.name[0]}</div>
                  <div>
                    <h3>{review.name}</h3>
                    <span>{review.role}</span>
                  </div>
                </div>
                <p>«{review.text}»</p>
              </article>
            ))}
          </div>
        </section>
      </main>

      <footer className="site-footer" id="footer-cta">
        <div className="container footer-grid">
          <div className="footer-copy">
            <span className="eyebrow">Контакт</span>
            <h2>{current.footerTitle}</h2>
            <p>{current.footerText}</p>
          </div>

          <div className="footer-actions glass-card">
            <a className="btn btn-primary" href="mailto:hello@kidquest-demo.ru?subject=KidQuest%20Call">Оставить заявку на звонок</a>
            <a className="btn btn-secondary" href="mailto:hello@kidquest-demo.ru?subject=KidQuest%20News">Подписаться на новости</a>
            <a className="btn btn-secondary" href="mailto:hello@kidquest-demo.ru?subject=KidQuest%20Offer">Получить скидку</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
