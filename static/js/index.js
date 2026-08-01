// Initialize Socket.IO connection
const socket = io();

// Cache DOM Elements for performance
const elements = {
    symbol: document.getElementById("symbol"),
    riskPercentage: document.getElementById("risk-percentage"),
    stopLoss: document.getElementById("stop-loss"),
    takeProfit: document.getElementById("take-profit"),
    maxOpenPositions: document.getElementById("max-open-positions"),
    maxDailyLoss: document.getElementById("max-daily-loss"),
    maxSpread: document.getElementById("max-spread"),
    startBtn: document.getElementById("start-btn"),
    stopBtn: document.getElementById("stop-btn"),
    symbolDisplay: document.getElementById("symbol-display"),
    priceDisplay: document.getElementById("price-display"),
    positionDisplay: document.getElementById("position-display"),
    statusDisplay: document.getElementById("status-display"),
    dailyDrawdown: document.getElementById("daily-drawdown"),
    dailyRiskStatus: document.getElementById("daily-risk-status"),
    openPositions: document.getElementById("open-positions"),
    alerts: document.getElementById("alerts")
};

// Event Listeners replacing inline HTML onclick attributes
elements.startBtn.addEventListener("click", startBot);
elements.stopBtn.addEventListener("click", stopBot);

function startBot() {
    const config = {
        symbol: elements.symbol.value,
        risk_percentage: parseFloat(elements.riskPercentage.value),
        stop_loss_pips: parseInt(elements.stopLoss.value, 10),
        take_profit_pips: parseInt(elements.takeProfit.value, 10),
        max_open_positions: parseInt(elements.maxOpenPositions.value, 10),
        max_daily_loss_percentage: parseFloat(elements.maxDailyLoss.value),
        max_spread_pips: parseFloat(elements.maxSpread.value)
    };

    console.log("Starting bot with config:", config);
    socket.emit("start_bot", config);
}

function stopBot() {
    console.log("Stopping bot");
    socket.emit("stop_bot");
}

socket.on("connect", function() {
    console.log("Connected to server via Socket.IO");
});

// Socket event bindings
socket.on("price_update", function(data) {
    console.log("Price update:", data);
    
    elements.symbolDisplay.innerText = data.symbol;
    elements.priceDisplay.innerText = data.price;
    elements.positionDisplay.innerText = data.position || "NONE";
    
    // Status text & style update
    if (data.running) {
        elements.statusDisplay.innerText = "RUNNING";
        elements.statusDisplay.className = "status-running";
    } else {
        elements.statusDisplay.innerText = "STOPPED";
        elements.statusDisplay.className = "status-stopped";
    }

    elements.dailyDrawdown.innerText = data.daily_drawdown.toFixed(2) + "%";
    elements.openPositions.innerText = data.open_positions;

    if (data.daily_loss_blocked) {
        elements.dailyRiskStatus.innerText = "TRADING BLOCKED";
        elements.dailyRiskStatus.className = "status-blocked";
    } else {
        elements.dailyRiskStatus.innerText = "ACTIVE";
        elements.dailyRiskStatus.className = "status-active";
    }
});

socket.on("bot_status", function(data) {
    elements.startBtn.disabled = data.running;
    elements.stopBtn.disabled = !data.running;
});

socket.on("alert", function(data) {
    const alertItem = document.createElement("p");
    alertItem.innerText = data.message;
    
    // Auto-scroll alerts to the latest event
    elements.alerts.appendChild(alertItem);
    elements.alerts.scrollTop = elements.alerts.scrollHeight;
});