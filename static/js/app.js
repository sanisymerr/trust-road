document.addEventListener("DOMContentLoaded", () => {
    const converterRows = window.TRUSTROAD_ROWS || [];
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

    let converterMode = "mng";

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
        input.value = code;

        document.querySelectorAll(`.currency-chip[data-target="${target}"]`).forEach((chip) => {
            chip.classList.toggle("currency-chip--active", chip.dataset.code === code);
        });
    }

    function resetResults() {
        mongolResult.textContent = "—";
        capitronResult.textContent = "—";
        cbrResult.textContent = "—";
    }

    function syncSelectionVisibility() {
        if (converterMode !== "cbr") return;

        if (convertFrom.value === "MNT") {
            setChipValue("from", "USD");
        }

        if (convertTo.value === "MNT") {
            setChipValue("to", convertFrom.value === "USD" ? "EUR" : "USD");
        }
    }

    function setConverterMode(mode) {
        converterMode = mode;
        modeButtons.forEach((button) => {
            button.classList.toggle("mode-switch__button--active", button.dataset.mode === mode);
        });

        if (mode === "cbr") {
            mongolResultCard.classList.add("is-hidden");
            capitronResultCard.classList.add("is-hidden");
            cbrResultCard.classList.remove("is-hidden");
            converterResults.classList.add("converter-results--single");
            converterSubtitle.textContent = "Режим ЦБ РФ считает любые пары, кроме MNT, потому что для MNT у ЦБ РФ нет собственного курса.";
            syncSelectionVisibility();
        } else {
            mongolResultCard.classList.remove("is-hidden");
            capitronResultCard.classList.remove("is-hidden");
            cbrResultCard.classList.add("is-hidden");
            converterResults.classList.remove("converter-results--single");
            converterSubtitle.textContent = "Режим Монголбанк + Capitron считает по выбранной дате и сразу показывает два результата.";

            if (convertFrom.value === convertTo.value) {
                setChipValue("to", convertTo.value === "USD" ? "MNT" : "USD");
            }
        }

        updateConverter();
    }

    function updateConverter() {
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
            cbrResult.textContent = formatResult(cbrValue, toCode);
            return;
        }

        const mongolValue = convertByRate(amount, fromRates.mongol, toRates.mongol);
        const capitronValue = convertByRate(amount, fromRates.capitron, toRates.capitron);
        mongolResult.textContent = formatResult(mongolValue, toCode);
        capitronResult.textContent = formatResult(capitronValue, toCode);
    }

    currencyChips.forEach((chip) => {
        chip.addEventListener("click", () => {
            const target = chip.dataset.target;
            const code = chip.dataset.code;
            setChipValue(target, code);

            if (converterMode === "cbr") {
                syncSelectionVisibility();
            }

            if (convertFrom.value === convertTo.value) {
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
            const previousFrom = convertFrom.value;
            setChipValue("from", convertTo.value);
            setChipValue("to", previousFrom);
            syncSelectionVisibility();

            if (convertFrom.value === convertTo.value) {
                setChipValue("to", convertTo.value === "USD" ? "EUR" : "USD");
            }

            updateConverter();
        });
    }

    convertAmount.addEventListener("input", updateConverter);

    setConverterMode("mng");
});
