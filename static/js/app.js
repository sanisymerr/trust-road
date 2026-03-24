document.addEventListener("DOMContentLoaded", () => {
    const converterRows = Array.isArray(window.TRUSTROAD_ROWS) ? window.TRUSTROAD_ROWS : [];
    const csrfToken = window.TRUSTROAD_CSRF || "";

    const convertFrom = document.getElementById("convertFrom");
    const convertTo = document.getElementById("convertTo");
    const convertAmount = document.getElementById("convertAmount");
    const swapCurrencies = document.getElementById("swapCurrencies");

    const mongolResult = document.getElementById("mongolResult");
    const capitronResult = document.getElementById("capitronResult");
    const cbrResult = document.getElementById("cbrResult");

    const mongolResultCard = document.getElementById("mongolResultCard");
    const capitronResultCard = document.getElementById("capitronResultCard");
    const cbrResultCard = document.getElementById("cbrResultCard");
    const converterResults = document.getElementById("converterResults");
    const converterSubtitle = document.getElementById("converterSubtitle");

    const currencyChips = document.querySelectorAll(".currency-chip");
    const modeButtons = document.querySelectorAll(".mode-switch__button");

    const refreshForm = document.getElementById("refreshForm");
    const refreshButton = document.getElementById("refreshButton");
    const updateStatusTitle = document.getElementById("updateStatusTitle");
    const updateStatusMessage = document.getElementById("updateStatusMessage");
    const updateStatusBadge = document.getElementById("updateStatusBadge");
    const statusResult = document.getElementById("statusResult");
    const statusStartedAt = document.getElementById("statusStartedAt");
    const statusFinishedAt = document.getElementById("statusFinishedAt");
    const statusLatestUpdate = document.getElementById("statusLatestUpdate");
    const heroComplimentText = document.getElementById("heroComplimentText");

    const compliments = [
        "Я минималистичный конвертер, а вы сегодня выглядите так, будто весь день решил быть на вашей стороне.",
        "Я минималистичный конвертер, а ваша улыбка сегодня могла бы спокойно победить любой плохой день.",
        "Я минималистичный конвертер, а у вас сегодня тот редкий вайб, который невозможно не заметить.",
        "Я минималистичный конвертер, а вы сегодня выглядите так красиво, что даже цифры рядом стараются быть аккуратнее.",
        "Я минималистичный конвертер, а ваша красота сегодня вообще без права на возражения.",
        "Я минималистичный конвертер, а у вас сегодня тот самый уровень, когда комплименты буквально пишутся сами.",
        "Я минималистичный конвертер, а вы сегодня выглядите как причина чьего-то хорошего настроения.",
        "Я минималистичный конвертер, а ваш взгляд сегодня слишком хорош, чтобы остаться без комплимента.",
        "Я минималистичный конвертер, а у вас сегодня энергия девушки, которой хочется сказать: вы просто вау.",
    ];

    let converterMode = "mng";
    let statusPollTimer = null;
    let lastSeenLatestUpdate = statusLatestUpdate ? statusLatestUpdate.textContent.trim() : "";

    function parseRate(value) {
        if (value === null || value === undefined) return null;
        const normalized = String(value).replace(/\s/g, "").replace(/,/g, "");
        const num = Number(normalized);
        return Number.isFinite(num) ? num : null;
    }

    function formatResult(value, currency) {
        if (!Number.isFinite(value)) return "—";
        const formatted = value.toLocaleString("ru-RU", {
            minimumFractionDigits: 0,
            maximumFractionDigits: 6,
        });
        return `${formatted} ${currency}`;
    }

    function convertByRate(amount, fromRate, toRate) {
        if (!Number.isFinite(amount) || amount < 0) return null;
        if (!Number.isFinite(fromRate) || !Number.isFinite(toRate) || toRate === 0) return null;
        return (amount * fromRate) / toRate;
    }

    function buildRateMap() {
        const map = {};

        converterRows.forEach((row) => {
            if (!row || !row.code) return;
            map[row.code] = {
                mongol: row.code === "MNT" ? 1 : parseRate(row.mongol_bank_mnt),
                capitron: row.code === "MNT" ? 1 : parseRate(row.capitron_mnt),
                cbr: row.code === "RUB" ? 1 : parseRate(row.cbr_rate_rub),
            };
        });

        if (!map.MNT) {
            map.MNT = { mongol: 1, capitron: 1, cbr: null };
        } else {
            map.MNT.mongol = 1;
            map.MNT.capitron = 1;
            map.MNT.cbr = parseRate(map.MNT.cbr);
        }

        if (!map.RUB) {
            map.RUB = { mongol: null, capitron: null, cbr: 1 };
        } else {
            map.RUB.cbr = 1;
        }

        return map;
    }

    const rateMap = buildRateMap();

    function setChipValue(target, code) {
        const input = target === "from" ? convertFrom : convertTo;
        if (!input) return;
        input.value = code;

        document.querySelectorAll(`.currency-chip[data-target="${target}"]`).forEach((chip) => {
            chip.classList.toggle("currency-chip--active", chip.dataset.code === code);
        });
    }

    function resetResults() {
        if (mongolResult) mongolResult.textContent = "—";
        if (capitronResult) capitronResult.textContent = "—";
        if (cbrResult) cbrResult.textContent = "—";
    }

    function startComplimentRotation() {
        if (!heroComplimentText || compliments.length === 0) return;

        let currentIndex = Math.floor(Math.random() * compliments.length);
        heroComplimentText.textContent = compliments[currentIndex];

        window.setInterval(() => {
            let nextIndex = currentIndex;
            while (compliments.length > 1 && nextIndex === currentIndex) {
                nextIndex = Math.floor(Math.random() * compliments.length);
            }
            currentIndex = nextIndex;
            heroComplimentText.textContent = compliments[currentIndex];
        }, 12000);
    }

    function setConverterMode(mode) {
        converterMode = mode;
        modeButtons.forEach((button) => {
            button.classList.toggle("mode-switch__button--active", button.dataset.mode === mode);
        });

        if (mode === "cbr") {
            mongolResultCard?.classList.add("is-hidden");
            capitronResultCard?.classList.add("is-hidden");
            cbrResultCard?.classList.remove("is-hidden");
            converterResults?.classList.add("converter-results--single");
            if (converterSubtitle) {
                converterSubtitle.textContent = "Режим ЦБ РФ считает пары через рублёвые курсы ЦБ РФ, включая конвертацию между RUB и MNT.";
            }
        } else {
            mongolResultCard?.classList.remove("is-hidden");
            capitronResultCard?.classList.remove("is-hidden");
            cbrResultCard?.classList.add("is-hidden");
            converterResults?.classList.remove("converter-results--single");
            if (converterSubtitle) {
                converterSubtitle.textContent = "Сравнивайте итог по официальному курсу Монголбанка и по банковскому курсу Capitron для одной и той же суммы.";
            }

            if (convertFrom && convertTo && convertFrom.value === convertTo.value) {
                setChipValue("to", convertTo.value === "USD" ? "MNT" : "USD");
            }
        }

        updateConverter();
    }

    function updateConverter() {
        if (!convertFrom || !convertTo || !convertAmount) return;

        const fromCode = convertFrom.value;
        const toCode = convertTo.value;
        const amountRaw = convertAmount.value.trim().replace(",", ".");
        const amount = Number(amountRaw);
        const fromRates = rateMap[fromCode];
        const toRates = rateMap[toCode];

        resetResults();
        if (!amountRaw || !fromRates || !toRates || !Number.isFinite(amount)) return;

        if (converterMode === "cbr") {
            const cbrValue = convertByRate(amount, fromRates.cbr, toRates.cbr);
            if (cbrResult) cbrResult.textContent = formatResult(cbrValue, toCode);
            return;
        }

        const mongolValue = convertByRate(amount, fromRates.mongol, toRates.mongol);
        const capitronValue = convertByRate(amount, fromRates.capitron, toRates.capitron);
        if (mongolResult) mongolResult.textContent = formatResult(mongolValue, toCode);
        if (capitronResult) capitronResult.textContent = formatResult(capitronValue, toCode);
    }

    function applyStatusPayload(status) {
        if (!status) return;

        const isRunning = Boolean(status.is_running);
        const statusName = isRunning ? "running" : (status.last_status || "idle");
        const badgeText = isRunning
            ? "в процессе"
            : statusName === "success"
                ? "успешно"
                : statusName === "error"
                    ? "ошибка"
                    : "ожидание";

        if (updateStatusTitle) {
            updateStatusTitle.textContent = isRunning
                ? "Идёт обновление"
                : statusName === "success"
                    ? "Последнее обновление прошло успешно"
                    : statusName === "error"
                        ? "Последнее обновление завершилось с ошибкой"
                        : "Система готова к обновлению";
        }

        if (updateStatusMessage) {
            updateStatusMessage.textContent = status.last_message || "—";
        }

        if (updateStatusBadge) {
            updateStatusBadge.textContent = badgeText;
            updateStatusBadge.className = `status-pill status-pill--${statusName}`;
        }

        if (statusResult) {
            statusResult.textContent = isRunning
                ? "в процессе"
                : statusName === "success"
                    ? "успешно"
                    : statusName === "error"
                        ? "неуспешно"
                        : "ожидание";
        }
        if (statusStartedAt) statusStartedAt.textContent = status.last_started_at || "—";
        if (statusFinishedAt) statusFinishedAt.textContent = status.last_finished_at || "—";
        if (statusLatestUpdate) statusLatestUpdate.textContent = status.latest_updated_at_vladivostok || "—";

        if (refreshButton) {
            refreshButton.disabled = isRunning;
            refreshButton.textContent = isRunning ? "Обновление идёт…" : "Обновить данные";
        }

        const latestUpdate = (status.latest_updated_at_vladivostok || "").trim();
        if (!isRunning && latestUpdate && latestUpdate !== lastSeenLatestUpdate && lastSeenLatestUpdate) {
            window.location.reload();
            return;
        }

        if (latestUpdate) {
            lastSeenLatestUpdate = latestUpdate;
        }
    }

    async function fetchStatus() {
        try {
            const response = await fetch("/api/update-status", { cache: "no-store" });
            if (!response.ok) return;
            const status = await response.json();
            applyStatusPayload(status);

            if (status.is_running) {
                if (!statusPollTimer) {
                    statusPollTimer = window.setInterval(fetchStatus, 3000);
                }
            } else if (statusPollTimer) {
                window.clearInterval(statusPollTimer);
                statusPollTimer = null;
            }
        } catch (_error) {
            // тихо игнорируем сетевые ошибки, чтобы не ломать интерфейс
        }
    }

    if (refreshForm) {
        refreshForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            if (!refreshButton || refreshButton.disabled) return;

            refreshButton.disabled = true;
            refreshButton.textContent = "Запуск…";

            try {
                const body = new URLSearchParams({ csrf_token: csrfToken });
                const response = await fetch("/refresh", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                        "Accept": "application/json",
                        "X-Requested-With": "fetch",
                        "X-CSRF-Token": csrfToken,
                    },
                    body: body.toString(),
                });

                const payload = await response.json().catch(() => ({ ok: false, message: "Не удалось прочитать ответ сервера." }));

                if (!response.ok && response.status !== 409) {
                    throw new Error(payload.message || "Ошибка запуска обновления.");
                }

                applyStatusPayload({
                    is_running: response.ok,
                    last_status: response.ok ? "running" : "error",
                    last_message: payload.message || (response.ok ? "Обновление запущено." : "Обновление уже выполняется."),
                    last_started_at: statusStartedAt?.textContent || "—",
                    last_finished_at: statusFinishedAt?.textContent || "—",
                    latest_updated_at_vladivostok: statusLatestUpdate?.textContent || "—",
                });

                await fetchStatus();
                if (!statusPollTimer) {
                    statusPollTimer = window.setInterval(fetchStatus, 3000);
                }
            } catch (error) {
                applyStatusPayload({
                    is_running: false,
                    last_status: "error",
                    last_message: error.message || "Не удалось запустить обновление.",
                    last_started_at: statusStartedAt?.textContent || "—",
                    last_finished_at: statusFinishedAt?.textContent || "—",
                    latest_updated_at_vladivostok: statusLatestUpdate?.textContent || "—",
                });
            }
        });
    }

    currencyChips.forEach((chip) => {
        chip.addEventListener("click", () => {
            const target = chip.dataset.target;
            const code = chip.dataset.code;
            setChipValue(target, code);

            if (convertFrom && convertTo && convertFrom.value === convertTo.value) {
                if (target === "from") {
                    setChipValue("to", code === "USD" ? "EUR" : "USD");
                } else {
                    setChipValue("from", code === "USD" ? "EUR" : "USD");
                }
            }

            updateConverter();
        });
    });

    modeButtons.forEach((button) => {
        button.addEventListener("click", () => {
            setConverterMode(button.dataset.mode);
        });
    });

    if (swapCurrencies) {
        swapCurrencies.addEventListener("click", () => {
            if (!convertFrom || !convertTo) return;
            const previousFrom = convertFrom.value;
            setChipValue("from", convertTo.value);
            setChipValue("to", previousFrom);
            if (convertFrom.value === convertTo.value) {
                setChipValue("to", convertTo.value === "USD" ? "EUR" : "USD");
            }

            updateConverter();
        });
    }

    convertAmount?.addEventListener("input", updateConverter);

    startComplimentRotation();
    setConverterMode("mng");
    fetchStatus();
});
