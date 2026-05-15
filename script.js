// script.js

let currentData = [];  // stores the loaded stocks

const container = document.getElementById("stockContainer");
const sortSelect = document.getElementById("sortSelect");
const refreshBtn = document.getElementById("refreshBtn");
const updateBar = document.getElementById("updateBar");

// Helper: get percentage position for a value between min and max (clamped)
function getPosition(value, minVal, maxVal) {
    if (maxVal === minVal) return 50;
    let pct = ((value - minVal) / (maxVal - minVal)) * 100;
    return Math.min(100, Math.max(0, pct));
}

// Create a single stock card
function createCard(stock) {
    const positive = stock.change >= 0;
    const card = document.createElement("div");
    card.className = "stock-card";

    // ---- EMA Structure positions (based on actual values) ----
    const values = [stock.price, stock.ema20, stock.ema50, stock.ema100, stock.ema200];
    const minVal = Math.min(...values);
    const maxVal = Math.max(...values);
    const posPrice = getPosition(stock.price, minVal, maxVal);
    const pos20 = getPosition(stock.ema20, minVal, maxVal);
    const pos50 = getPosition(stock.ema50, minVal, maxVal);
    const pos100 = getPosition(stock.ema100, minVal, maxVal);
    const pos200 = getPosition(stock.ema200, minVal, maxVal);

    // ---- Day Range position (price between low and high) ----
    let rangePos = 50;
    if (stock.high !== stock.low) {
        rangePos = ((stock.price - stock.low) / (stock.high - stock.low)) * 100;
        rangePos = Math.min(100, Math.max(0, rangePos));
    }

    card.innerHTML = `
    <div class="left-section">
        <div>
            <div class="stock-name">${stock.symbol}</div>
            <div class="company">${stock.symbol} (NSE)</div>
        </div>
        <div class="price-row">
            <div class="price">₹${stock.price.toLocaleString()}</div>
            <div class="change ${positive ? "positive" : "negative"}">
                ${positive ? "+" : ""}${stock.change}%
            </div>
        </div>
        <div class="ema-values">
            <div class="ema-box"><div class="ema-label ema20">E20</div><div class="ema-price">${stock.ema20}</div></div>
            <div class="ema-box"><div class="ema-label ema50">E50</div><div class="ema-price">${stock.ema50}</div></div>
            <div class="ema-box"><div class="ema-label ema100">E100</div><div class="ema-price">${stock.ema100}</div></div>
            <div class="ema-box"><div class="ema-label ema200">E200</div><div class="ema-price">${stock.ema200}</div></div>
        </div>
    </div>
    <div class="middle-section">
        <div class="section-title">EMA STRUCTURE</div>
        <div class="line-area">
            <div class="base-line"></div>
            <div class="circle c200" style="left:${pos200}%"></div>
            <div class="circle c100" style="left:${pos100}%"></div>
            <div class="circle c50" style="left:${pos50}%"></div>
            <div class="circle c20" style="left:${pos20}%"></div>
            <div class="triangle" style="left:${posPrice}%"></div>
        </div>
    </div>
    <div class="right-section">
        <div class="section-title">DAY RANGE</div>
        <div class="line-area">
            <div class="base-line"></div>
            <div class="range-dot low"></div>
            <div class="range-dot high"></div>
            <div class="triangle" style="left:${rangePos}%"></div>
        </div>
        <div class="range-labels">
            <span>${stock.low}<div class="low-text">LOW</div></span>
            <span style="text-align:right">${stock.high}<div class="high-text">HIGH</div></span>
        </div>
    </div>
    `;
    return card;
}

// Render all cards based on currentData
function renderCards() {
    container.innerHTML = "";
    currentData.forEach(stock => {
        container.appendChild(createCard(stock));
    });
}

// Sorting function
function sortData(criterion) {
    if (criterion === "score") {
        currentData.sort((a, b) => b.score - a.score);
    } else if (criterion === "price") {
        currentData.sort((a, b) => b.price - a.price);
    } else if (criterion === "symbol") {
        currentData.sort((a, b) => a.symbol.localeCompare(b.symbol));
    }
    renderCards();
}

// Load data from data/results.json
async function loadData() {
    try {
        updateBar.innerText = "● Last update: Loading...";
        const response = await fetch("data/results.json?" + Date.now()); // cache buster
        if (!response.ok) throw new Error("Failed to fetch data");
        const json = await response.json();
        currentData = json.data;
        updateBar.innerText = `● Last update: ${json.last_updated}`;
        // Apply current sort selection
        const currentSort = sortSelect.value;
        sortData(currentSort);
    } catch (error) {
        console.error(error);
        updateBar.innerText = "● Error loading data. Please check that data/results.json exists.";
        container.innerHTML = "<div style='color:red; text-align:center'>Could not load stock data. Run scanner.py first.</div>";
    }
}

// Event listeners
sortSelect.addEventListener("change", (e) => {
    sortData(e.target.value);
});

refreshBtn.addEventListener("click", () => {
    loadData();
});

// Initial load
loadData();
