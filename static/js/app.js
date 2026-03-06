async function loadRates(force = false) {
  const statusEl = document.getElementById("status");
  const tableBody = document.getElementById("rates-body");

  try {
    if (statusEl) statusEl.textContent = "Загрузка курсов...";
    if (tableBody) tableBody.innerHTML = "";

    const response = await fetch(`/api/rates${force ? "?force=1" : ""}`);
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
          ? "Live-курсы недоступны, показан последний сохранённый cache."
          : "Курсы загружены.";
    }
  } catch (error) {
    console.error(error);
    if (statusEl) {
      statusEl.textContent = error.message || "Ошибка загрузки курсов.";
    }
  }
}

function fillCurrencySelect(rates) {
  const select = document.getElementById("currency");
  if (!select) return;

  const currentValue = select.value;
  select.innerHTML = "";

  rates.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.code;
    option.textContent = `${item.code} — ${item.name || item.code}`;
    select.appendChild(option);
  });

  if (currentValue && rates.some((x) => x.code === currentValue)) {
    select.value = currentValue;
  }
}

async function calculate() {
  const amount = document.getElementById("amount")?.value;
  const currency = document.getElementById("currency")?.value;
  const mntEl = document.getElementById("result-mnt");
  const rubEl = document.getElementById("result-rub");

  if (!amount || !currency) {
    if (mntEl) mntEl.textContent = "—";
    if (rubEl) rubEl.textContent = "—";
    return;
  }

  try {
    const response = await fetch(
      `/api/convert?amount=${encodeURIComponent(amount)}&currency=${encodeURIComponent(currency)}`
    );
    const data = await response.json();

    if (!data.ok) {
      throw new Error(data.error || "Ошибка расчёта");
    }

    if (mntEl) mntEl.textContent = formatNumber(data.total_mnt);
    if (rubEl) rubEl.textContent = formatNumber(data.total_rub);
  } catch (error) {
    console.error(error);
    if (mntEl) mntEl.textContent = "Ошибка";
    if (rubEl) rubEl.textContent = "Ошибка";
  }
}

function formatNumber(value) {
  const num = Number(value);
  if (Number.isNaN(num)) return "—";
  return num.toLocaleString("ru-RU", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("reload-rates")?.addEventListener("click", () => loadRates(true));
  document.getElementById("amount")?.addEventListener("input", calculate);
  document.getElementById("currency")?.addEventListener("change", calculate);
  loadRates(false);
});