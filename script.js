// API Configuration - automatically uses current server URL
const API_BASE_URL = window.location.origin;
let productsData = [];

console.log('🚀 Dashboard starting...');
console.log('📍 API Base URL:', API_BASE_URL);

// Load statistics
async function loadStats() {
    try {
        console.log('📊 Fetching stats...');
        const response = await fetch(`${API_BASE_URL}/api/stats`);
        
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('✅ Stats loaded:', data);
        
        if (data.success) {
            document.getElementById('total-products').textContent = data.stats.total_products;
            document.getElementById('avg-price').textContent = `$${data.stats.average_price}`;
            document.getElementById('avg-rating').textContent = data.stats.average_rating;
            document.getElementById('prime-count').textContent = data.stats.prime_products;
        } else {
            console.error('❌ Stats error:', data.error);
        }
    } catch (error) {
        console.error('❌ Error loading stats:', error);
        document.getElementById('total-products').textContent = 'Error';
        document.getElementById('avg-price').textContent = 'Error';
        document.getElementById('avg-rating').textContent = 'Error';
        document.getElementById('prime-count').textContent = 'Error';
    }
}

// Load products
async function loadProducts() {
    try {
        console.log('📦 Fetching products...');
        const response = await fetch(`${API_BASE_URL}/api/products`);
        
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('✅ Products loaded:', data);
        
        if (data.success) {
            productsData = data.products;
            displayProducts(productsData);
        } else {
            showError('Failed to load products: ' + data.error);
        }
    } catch (error) {
        console.error('❌ Error loading products:', error);
        showError('Error connecting to API: ' + error.message);
    }
}

// Display products
function displayProducts(products) {
    const container = document.getElementById('products-container');
    
    if (!products || products.length === 0) {
        container.innerHTML = '<div class="loading">No products found. Please run scraper.py first.</div>';
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
                    ${product.list_price ? `<span style="text-decoration: line-through; font-size: 0.6em; color: #999; margin-left: 10px;">${product.currency}${product.list_price.toFixed(2)}</span>` : ''}
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
                    ${product.discount_percent ? `<span class="badge badge-discount">-${Math.round(product.discount_percent)}%</span>` : ''}
                    ${product.best_sellers_rank ? `<span class="badge badge-bsr">${product.best_sellers_rank}</span>` : ''}
                </div>
                
                ${product.bullet_points ? `
                    <div class="product-features">
                        <strong>Key Features:</strong>
                        <ul>
                            ${product.bullet_points.split('|').slice(0, 3).map(point => 
                                `<li>${point.trim()}</li>`
                            ).join('')}
                        </ul>
                    </div>
                ` : ''}
                
                <div class="product-asin">ASIN: ${product.asin}</div>
                <div class="product-footer">
                    <small>Scraped: ${new Date(product.scraped_at).toLocaleString()}</small>
                </div>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = `<div class="products-grid">${html}</div>`;
}

// Sort products
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

// Show error
function showError(message) {
    const container = document.getElementById('products-container');
    container.innerHTML = `
        <div class="error">
            <h3>⚠️ Error</h3>
            <p>${message}</p>
            <p>Please check:</p>
            <ul>
                <li>Database exists (amazon_products.db)</li>
                <li>Server is running</li>
                <li>Console for more details (F12)</li>
            </ul>
            <button onclick="location.reload()" style="padding: 10px 20px; margin-top: 10px; cursor: pointer; background: #667eea; color: white; border: none; border-radius: 5px;">Retry</button>
        </div>
    `;
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    console.log('🎯 DOM loaded, initializing...');
    
    // Add sort listener
    document.getElementById('sort-by').addEventListener('change', (e) => {
        console.log('🔄 Sorting by:', e.target.value);
        sortProducts(e.target.value);
    });
    
    // Initialize data loading
    loadStats();
    loadProducts();
});