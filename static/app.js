(() => {
  "use strict";

  function renumberFields() {
    document.querySelectorAll(".field-editor-row").forEach((row, index) => {
      const number = row.querySelector(".row-number");
      if (number) number.textContent = index + 1;
    });
  }

  const addFieldButton = document.getElementById("addFieldButton");
  const fieldsContainer = document.getElementById("fieldsContainer");
  const fieldRowTemplate = document.getElementById("fieldRowTemplate");

  if (addFieldButton && fieldsContainer && fieldRowTemplate) {
    addFieldButton.addEventListener("click", () => {
      fieldsContainer.appendChild(fieldRowTemplate.content.cloneNode(true));
      renumberFields();
      const firstInput = fieldsContainer.lastElementChild && fieldsContainer.lastElementChild.querySelector("input");
      if (firstInput) firstInput.focus();
    });

    fieldsContainer.addEventListener("click", event => {
      const copyButton = event.target.closest(".copy-language-field");
      if (copyButton) {
        const row = copyButton.closest(".field-editor-row");
        const source = row.querySelector('[name="value_ru[]"]');
        const target = row.querySelector('[name="value_en[]"]');
        if (source && target) {
          target.value = source.value;
          target.dispatchEvent(new Event("input", { bubbles: true }));
          copyButton.textContent = "Готово";
          window.setTimeout(() => { copyButton.textContent = "RU → EN"; }, 1000);
        }
        return;
      }

      const removeButton = event.target.closest(".remove-field");
      if (!removeButton) return;
      if (fieldsContainer.children.length <= 1) {
        alert("Должно остаться хотя бы одно поле.");
        return;
      }
      removeButton.closest(".field-editor-row").remove();
      renumberFields();
    });

    const fillEnglishButton = document.getElementById("fillEnglishButton");
    if (fillEnglishButton) {
      fillEnglishButton.addEventListener("click", () => {
        fieldsContainer.querySelectorAll(".field-editor-row").forEach(row => {
          const source = row.querySelector('[name="value_ru[]"]');
          const target = row.querySelector('[name="value_en[]"]');
          if (source && target && source.value.trim()) target.value = source.value;
        });
        const original = fillEnglishButton.textContent;
        fillEnglishButton.textContent = "Значения скопированы";
        window.setTimeout(() => { fillEnglishButton.textContent = original; }, 1200);
      });
    }

    renumberFields();
  }

  document.querySelectorAll("form[data-confirm]").forEach(form => {
    form.addEventListener("submit", event => {
      if (!confirm(form.dataset.confirm || "Продолжить?")) {
        event.preventDefault();
      }
    });
  });

  document.querySelectorAll("[data-copy-target]").forEach(button => {
    button.addEventListener("click", async () => {
      const target = document.querySelector(button.dataset.copyTarget);
      if (!target) return;
      await copyText(target.value || target.textContent || "");
      const previous = button.textContent;
      button.textContent = "Скопировано";
      setTimeout(() => button.textContent = previous, 1300);
    });
  });

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const helper = document.createElement("textarea");
      helper.value = text;
      helper.style.position = "fixed";
      helper.style.opacity = "0";
      document.body.appendChild(helper);
      helper.select();
      document.execCommand("copy");
      helper.remove();
    }
  }

  const paymentCard = document.getElementById("paymentCard");
  if (!paymentCard) return;

  let currentLanguage = "ru";
  const toast = document.getElementById("toast");
  const rows = [...document.querySelectorAll(".public-detail-row")];

  function showToast(message) {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add("visible");
    clearTimeout(showToast.timer);
    showToast.timer = setTimeout(() => toast.classList.remove("visible"), 1700);
  }

  function localized(element, lang) {
    return lang === "ru" ? element.dataset.textRu : element.dataset.textEn;
  }

  function setLanguage(lang) {
    currentLanguage = lang;
    document.documentElement.lang = lang;

    document.querySelectorAll(".lang-button").forEach(button => {
      button.classList.toggle("active", button.dataset.lang === lang);
    });

    document.querySelectorAll("[data-text-ru][data-text-en]").forEach(element => {
      const text = localized(element, lang);
      if (typeof text === "string") element.textContent = text;
    });

    const pageTitle = document.getElementById("pageTitle");
    const pageSubtitle = document.getElementById("pageSubtitle");
    if (pageTitle) {
      pageTitle.textContent = lang === "ru" ? paymentCard.dataset.titleRu : paymentCard.dataset.titleEn;
    }
    if (pageSubtitle) {
      pageSubtitle.textContent = lang === "ru" ? paymentCard.dataset.subtitleRu : paymentCard.dataset.subtitleEn;
      pageSubtitle.style.display = pageSubtitle.textContent ? "block" : "none";
    }

    const noteContainer = document.getElementById("publicNote");
    if (noteContainer) {
      const note = lang === "ru" ? paymentCard.dataset.noteRu : paymentCard.dataset.noteEn;
      noteContainer.querySelector("p").textContent = note;
      noteContainer.style.display = note ? "flex" : "none";
    }

    rows.forEach(row => {
      row.querySelector(".public-detail-label").textContent =
        lang === "ru" ? row.dataset.labelRu : row.dataset.labelEn;
      row.querySelector(".public-detail-value").textContent =
        lang === "ru" ? row.dataset.valueRu : row.dataset.valueEn;
      const copyButton = row.querySelector(".copy-icon-button");
      if (copyButton) {
        const label = lang === "ru" ? "Копировать значение" : "Copy value";
        copyButton.setAttribute("aria-label", label);
        copyButton.setAttribute("title", label);
      }
    });
  }

  document.querySelectorAll(".lang-button").forEach(button => {
    button.addEventListener("click", () => setLanguage(button.dataset.lang));
  });

  rows.forEach(row => {
    const rowCopyButton = row.querySelector(".copy-icon-button");
    if (rowCopyButton) rowCopyButton.addEventListener("click", async () => {
      const value = currentLanguage === "ru" ? row.dataset.valueRu : row.dataset.valueEn;
      await copyText(value);
      showToast(currentLanguage === "ru" ? "Скопировано" : "Copied");
    });
  });

  const copyAllPublic = document.getElementById("copyAllPublic");
  if (copyAllPublic) copyAllPublic.addEventListener("click", async () => {
    const text = rows.map(row => {
      const label = currentLanguage === "ru" ? row.dataset.labelRu : row.dataset.labelEn;
      const value = currentLanguage === "ru" ? row.dataset.valueRu : row.dataset.valueEn;
      return `${label}: ${value}`;
    }).join("\n");

    await copyText(text);
    showToast(currentLanguage === "ru" ? "Все данные скопированы" : "All details copied");
  });

  const sharePage = document.getElementById("sharePage");
  if (sharePage) sharePage.addEventListener("click", async () => {
    const shareData = {
      title: document.title,
      text: currentLanguage === "ru" ? "Данные для перевода" : "Payment details",
      url: window.location.href
    };

    if (navigator.share) {
      try {
        await navigator.share(shareData);
        return;
      } catch (error) {
        if (error.name === "AbortError") return;
      }
    }

    await copyText(window.location.href);
    showToast(currentLanguage === "ru" ? "Ссылка скопирована" : "Link copied");
  });

  setLanguage("ru");
})();
