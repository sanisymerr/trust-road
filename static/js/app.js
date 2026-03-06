async function loadRates(force = false) {
  const statusEl = document.getElementById("status");
  const tableBody = document.getElementById("rates-body");

  try {
    if (statusEl) statusEl.textContent = "Загрузка курсов...";
    if (tableBody) tableBody.innerHTML = "";

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 12000);

    const response = await fetch(`/api/rates${force ? "?force=1" : ""}`, {
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    const data = await response.json();

    if (!data.ok) {
      throw new Error(data.error || "Не удалось загрузить курсы");
    }

    const ratesObj = data.rates || {};
    const rates = Object.values(ratesObj);

    if (!rates.length) {
      if (statusEl) statusEl.textContent = "Курсы не найдены.";
      return;
    }

    rates.sort((a, b) => (a.code || "").localeCompare(b.code || ""));

    if (tableBody) {
      tableBody.innerHTML = "";

      rates.forEach((item) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${item.code || ""}</td>
          <td>${item.name || item.code || ""}</td>
          <td>${formatNumber(item.rate)}</td>
        `;

        tr.addEventListener("click", () => {
          const currencySelect = document.getElementById("currency");
          if (currencySelect) {
            currencySelect.value = item.code;
          }
          calculate();
        });

        tableBody.appendChild(tr);
      });
    }

    fillCurrencySelect(rates);

    const source = data.meta?.source || "unknown";
    if (statusEl) {
      statusEl.textContent =
        source === "capitron_live"
          ? "Курсы загружены с Capitron."
          : source === "cache"
          ? "Курсы загружены из cache."
          : source === "stale_cache"
          ? "Capitron недоступен, показан сохранённый курс."
          : source === "fallback"
          ? "Capitron недоступен, показаны резервные курсы."
          : "Курсы загружены.";
    }
  } catch (error) {
    console.error(error);
    if (statusEl) {
      statusEl.textContent = "Ошибка загрузки курсов.";
    }
  }
}

function fillCurrencySelect(rates) {
  const select = document.getElementById("currency");
  if (!select) return;

  const currentValue = select.value;
  select.innerHTML = "";

  // Добавить валюты
  const currencyList = [
    { code: 'USD', name: 'Ам доллар' },
    { code: 'EUR', name: 'Евро' },
    { code: 'CNY', name: 'Юань' },
    { code: 'JPY', name: 'Иен' },
    { code: 'KRW', name: 'Вон' },
    { code: 'GBP', name: 'Фунт' },
    { code: 'CHF', name: 'Франк' },
    { code: 'SGD', name: 'Сингапур доллар' },
    { code: 'HKD', name: 'Гонконг доллар' },
  ];

  currencyList.forEach((currency) => {
    const option = document.createElement("option");
    option.value = currency.code;
    option.textContent = `${currency.code} — ${currency.name}`;
    select.appendChild(option);
  });

  if (currentValue && rates.some((x) => x.code === currentValue)) {
    select.value = currentValue;
  }
}
