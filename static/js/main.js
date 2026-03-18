const CART_KEY = 'neonova_cart';

function formatPrice(value) {
    return `${new Intl.NumberFormat('ru-RU').format(value)} ₽`;
}

function getCart() {
    try {
        return JSON.parse(localStorage.getItem(CART_KEY)) || [];
    } catch (error) {
        return [];
    }
}

function saveCart(cart) {
    localStorage.setItem(CART_KEY, JSON.stringify(cart));
    updateCartCount();
}

function updateCartCount() {
    const badges = document.querySelectorAll('.cart-count-value');
    if (!badges.length) return;
    const count = getCart().reduce((sum, item) => sum + item.quantity, 0);
    badges.forEach(badge => {
        badge.textContent = count;
    });
}

function addToCart(product) {
    const cart = getCart();
    const existing = cart.find(item => item.id === product.id);
    if (existing) {
        existing.quantity += 1;
    } else {
        cart.push({ ...product, quantity: 1 });
    }
    saveCart(cart);
    showToast(`Добавлено: ${product.name}`);
}

function showToast(message) {
    let toast = document.querySelector('.floating-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.className = 'floating-toast';
        toast.style.position = 'fixed';
        toast.style.right = '22px';
        toast.style.bottom = '22px';
        toast.style.padding = '14px 18px';
        toast.style.borderRadius = '16px';
        toast.style.background = 'rgba(10, 20, 37, 0.94)';
        toast.style.border = '1px solid rgba(255,255,255,0.08)';
        toast.style.color = '#f4f8ff';
        toast.style.boxShadow = '0 18px 50px rgba(0,0,0,0.35)';
        toast.style.zIndex = '999';
        toast.style.transition = '0.3s ease';
        document.body.appendChild(toast);
    }

    toast.textContent = message;
    toast.style.opacity = '1';
    toast.style.transform = 'translateY(0)';

    clearTimeout(window.__toastTimer);
    window.__toastTimer = setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
    }, 1800);
}

function bindAddToCartButtons() {
    document.querySelectorAll('.add-to-cart').forEach(button => {
        button.addEventListener('click', () => {
            addToCart({
                id: Number(button.dataset.id),
                name: button.dataset.name,
                price: Number(button.dataset.price),
                image: button.dataset.image,
                slug: button.dataset.slug,
            });
        });
    });
}

function initCatalogDrawer() {
    const panel = document.getElementById('filters-panel');
    const overlay = document.getElementById('filters-overlay');
    const openButton = document.getElementById('open-filters');
    const closeButton = document.getElementById('close-filters');

    if (!panel || !overlay) return;

    const closeDrawer = () => {
        panel.classList.remove('open');
        overlay.classList.remove('open');
        document.body.classList.remove('drawer-open');
    };

    const openDrawer = () => {
        if (window.innerWidth > 760) return;
        panel.classList.add('open');
        overlay.classList.add('open');
        document.body.classList.add('drawer-open');
    };

    openButton?.addEventListener('click', openDrawer);
    closeButton?.addEventListener('click', closeDrawer);
    overlay.addEventListener('click', closeDrawer);

    window.addEventListener('resize', () => {
        if (window.innerWidth > 760) {
            closeDrawer();
        }
    });

    return closeDrawer;
}

function renderCatalog() {
    const grid = document.getElementById('catalog-grid');
    if (!grid) return;

    const cards = Array.from(grid.querySelectorAll('.catalog-product'));
    const searchInput = document.getElementById('search-input');
    const sortSelect = document.getElementById('sort-select');
    const sortButtons = Array.from(document.querySelectorAll('.sort-pill'));
    const priceRange = document.getElementById('price-range');
    const priceRangeValue = document.getElementById('price-range-value');
    const categoryCheckboxes = Array.from(document.querySelectorAll('.category-checkbox'));
    const resultsCount = document.getElementById('results-count');
    const emptyState = document.getElementById('empty-state');
    const resetButton = document.getElementById('reset-filters');
    const params = new URLSearchParams(window.location.search);
    const closeDrawer = initCatalogDrawer();

    const setSort = value => {
        sortSelect.value = value;
        sortButtons.forEach(button => {
            button.classList.toggle('active', button.dataset.sort === value);
        });
    };

    const initialCategory = params.get('category');
    if (initialCategory) {
        categoryCheckboxes.forEach(checkbox => {
            checkbox.checked = checkbox.value === initialCategory;
        });
    }

    const initialSearch = params.get('search');
    if (initialSearch) {
        searchInput.value = initialSearch;
    }

    function applyFilters() {
        const searchText = searchInput.value.trim().toLowerCase();
        const selectedCategories = categoryCheckboxes.filter(cb => cb.checked).map(cb => cb.value);
        const maxPrice = Number(priceRange.value);
        priceRangeValue.textContent = formatPrice(maxPrice);

        cards.forEach(card => {
            const name = card.dataset.name;
            const category = card.dataset.category;
            const price = Number(card.dataset.price);
            const matchesSearch = name.includes(searchText);
            const matchesCategory = selectedCategories.length ? selectedCategories.includes(category) : true;
            const matchesPrice = price <= maxPrice;
            const visible = matchesSearch && matchesCategory && matchesPrice;
            card.classList.toggle('hidden', !visible);
        });

        const visibleCards = cards.filter(card => !card.classList.contains('hidden'));
        const sortValue = sortSelect.value;

        visibleCards.sort((a, b) => {
            const priceA = Number(a.dataset.price);
            const priceB = Number(b.dataset.price);
            const ratingA = Number(a.dataset.rating);
            const ratingB = Number(b.dataset.rating);
            const nameA = a.dataset.displayName;
            const nameB = b.dataset.displayName;

            switch (sortValue) {
                case 'price-asc':
                    return priceA - priceB;
                case 'price-desc':
                    return priceB - priceA;
                case 'name-asc':
                    return nameA.localeCompare(nameB, 'ru');
                case 'name-desc':
                    return nameB.localeCompare(nameA, 'ru');
                case 'rating-desc':
                    return ratingB - ratingA;
                default:
                    return ratingB - ratingA;
            }
        });

        visibleCards.forEach(card => grid.appendChild(card));
        resultsCount.textContent = `Найдено товаров: ${visibleCards.length}`;
        emptyState.classList.toggle('hidden', visibleCards.length !== 0);
    }

    [searchInput, priceRange, ...categoryCheckboxes].forEach(element => {
        element.addEventListener('input', applyFilters);
        element.addEventListener('change', applyFilters);
    });

    sortButtons.forEach(button => {
        button.addEventListener('click', () => {
            setSort(button.dataset.sort);
            applyFilters();
            if (window.innerWidth <= 760) {
                closeDrawer?.();
            }
        });
    });

    resetButton?.addEventListener('click', () => {
        searchInput.value = '';
        priceRange.value = priceRange.max;
        categoryCheckboxes.forEach(cb => (cb.checked = false));
        setSort('popular');
        applyFilters();
        history.replaceState({}, '', window.location.pathname);
    });

    setSort(sortSelect.value || 'popular');
    applyFilters();
}

function renderCartPage() {
    const cartContainer = document.getElementById('cart-items');
    if (!cartContainer) return;

    const summaryCount = document.getElementById('summary-count');
    const summaryTotal = document.getElementById('summary-total');
    const template = document.getElementById('cart-item-template');
    const checkoutButton = document.getElementById('checkout-button');

    function draw() {
        const cart = getCart();
        cartContainer.innerHTML = '';

        if (!cart.length) {
            cartContainer.innerHTML = `
                <div class="empty-catalog">
                    <h3>Корзина пока пустая</h3>
                    <p>Добавь товары из каталога — они сразу появятся здесь.</p>
                </div>
            `;
        }

        let totalCount = 0;
        let totalPrice = 0;

        cart.forEach(item => {
            totalCount += item.quantity;
            totalPrice += item.price * item.quantity;

            const node = template.content.cloneNode(true);
            const image = node.querySelector('.cart-item-image');
            const title = node.querySelector('.cart-item-title');
            const price = node.querySelector('.cart-item-price');
            const qtyValue = node.querySelector('.qty-value');
            const lineTotal = node.querySelector('.cart-line-total');
            const minus = node.querySelector('.minus');
            const plus = node.querySelector('.plus');
            const remove = node.querySelector('.remove-item');

            image.src = item.image;
            image.alt = item.name;
            title.textContent = item.name;
            title.href = `/product/${item.slug}`;
            price.textContent = formatPrice(item.price);
            qtyValue.textContent = item.quantity;
            lineTotal.textContent = formatPrice(item.price * item.quantity);

            minus.addEventListener('click', () => {
                const cartState = getCart();
                const current = cartState.find(product => product.id === item.id);
                if (!current) return;
                current.quantity -= 1;
                const next = cartState.filter(product => product.quantity > 0);
                saveCart(next);
                draw();
            });

            plus.addEventListener('click', () => {
                const cartState = getCart();
                const current = cartState.find(product => product.id === item.id);
                if (!current) return;
                current.quantity += 1;
                saveCart(cartState);
                draw();
            });

            remove.addEventListener('click', () => {
                const next = getCart().filter(product => product.id !== item.id);
                saveCart(next);
                draw();
            });

            cartContainer.appendChild(node);
        });

        summaryCount.textContent = totalCount;
        summaryTotal.textContent = formatPrice(totalPrice);
    }

    checkoutButton?.addEventListener('click', () => {
        const cart = getCart();
        if (!cart.length) {
            showToast('Сначала добавь товар в корзину');
            return;
        }
        showToast('Демо: оформление заказа можно подключить позже');
    });

    draw();
}

function initReveal() {
    const elements = document.querySelectorAll('.reveal');
    if (!elements.length) return;

    const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('in-view');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.14 });

    elements.forEach(element => observer.observe(element));
}

function initBackToTop() {
    const button = document.getElementById('back-to-top');
    if (!button) return;

    const toggleButton = () => {
        button.classList.toggle('visible', window.scrollY > 500);
    };

    button.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    window.addEventListener('scroll', toggleButton);
    toggleButton();
}

document.addEventListener('DOMContentLoaded', () => {
    updateCartCount();
    bindAddToCartButtons();
    renderCatalog();
    renderCartPage();
    initReveal();
    initBackToTop();
});
