const API_URL = 'https://unmuscled-mucic-kamden.ngrok-free.dev/api';
let productsData = [];

async function loadStats() {
    try {
        const response = await fetch(`${API_URL}/stats`);
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('total-products').textContent = data.stats.total_products;
            document.getElementById('avg-price').textContent = `$${data.stats.average_price}`;
            document.getElementById('avg-rating').textContent = data.stats.average_rating;
            document.getElementById('prime-count').textContent = data.stats.prime_products;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

async function loadProducts() {
    try {
        const response = await fetch(`${API_URL}/products`);
        const data = await response.json();
        
        if (data.success) {
            productsData = data.products;
            displayProducts(productsData);
        } else {
            showError('Failed to load products');
        }
    } catch (error) {
        showError('Error connecting to API: ' + error.message);
    }
}

// Відображення товарів
function displayProducts(products) {
    const container = document.getElementById('products-container');
    
    if (products.length === 0) {
        container.innerHTML = '<div class="loading">No products found</div>';
        return;
    }

    const html = products.map(product => `
        <div class="product-card">
            <img src="${product.main_image_url || 'https://via.placeholder.com/300x250?text=No+Image'}" 
                 alt="${product.title}" 
                 class="product-image"
                 onerror="this.src='https://via.placeholder.com/300x250?text=No+Image'">
            <div class="product-info">
                <span class="product-rank">#${product.rank}</span>
                <h3 class="product-title">${product.title}</h3>
                
                <div class="product-price">
                    ${product.currency}${product.price.toFixed(2)}
                    ${product.list_price ? `<span style="text-decoration: line-through; font-size: 0.6em; color: #999; margin-left: 10px;">$${product.list_price.toFixed(2)}</span>` : ''}
                </div>
                
                ${product.rating ? `
                    <div class="product-rating">
                        <span class="stars">${'★'.repeat(Math.round(product.rating))}${'☆'.repeat(5 - Math.round(product.rating))}</span>
                        <span>${product.rating}/5.0</span>
                        ${product.reviews_count ? `<span class="reviews-count">(${product.reviews_count.toLocaleString()} reviews)</span>` : ''}
                    </div>
                ` : ''}
                
                <div class="product-badges">
                    ${product.is_prime ? '<span class="badge badge-prime">Prime</span>' : ''}
                    ${product.discount_percent ? `<span class="badge badge-discount">-${product.discount_percent}%</span>` : ''}
                    ${product.best_sellers_rank ? `<span class="badge badge-bsr">${product.best_sellers_rank}</span>` : ''}
                </div>
                
                <div class="product-asin">ASIN: ${product.asin}</div>
            </div>
        </div>
    `).join('');

    container.innerHTML = `<div class="products-grid">${html}</div>`;
}

// Сортування товарів
function sortProducts(sortBy) {
    let sorted = [...productsData];
    
    switch(sortBy) {
        case 'price-asc':
            sorted.sort((a, b) => (a.price || 0) - (b.price || 0));
            break;
        case 'price-desc':
            sorted.sort((a, b) => (b.price || 0) - (a.price || 0));
            break;
        case 'rating-desc':
            sorted.sort((a, b) => (b.rating || 0) - (a.rating || 0));
            break;
        case 'rating-asc':
            sorted.sort((a, b) => (a.rating || 0) - (b.rating || 0));
            break;
        default:
            sorted.sort((a, b) => a.rank - b.rank);
    }
    
    displayProducts(sorted);
}

// Показати помилку
function showError(message) {
    const container = document.getElementById('products-container');
    container.innerHTML = `<div class="error">${message}</div>`;
}

// Event listeners
document.getElementById('sort-by').addEventListener('change', (e) => {
    sortProducts(e.target.value);
});

// Ініціалізація
loadStats();
loadProducts();