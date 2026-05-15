async function loadData(){

    const response = await fetch("data/results.json");

    const result = await response.json();

    const stocks = result.data;

    const stockList = document.getElementById("stockList");

    stockList.innerHTML = "";

    stocks.forEach(stock => {

        const maxValue = Math.max(
            stock.price,
            stock.ema20,
            stock.ema50,
            stock.ema100,
            stock.ema200
        );

        const card = document.createElement("div");

        card.className = "stock-card";

        card.innerHTML = `

            <div class="stock-header">

                <div>
                    <h2>${stock.symbol}</h2>
                    <h3>₹${stock.price}</h3>
                </div>

                <div>
                    Score: ${stock.score}
                </div>

            </div>

            <div class="details">

                <p>EMA20 : ${stock.ema20}</p>

                <div class="bar">
                    <div class="fill ema20"
                    style="width:${(stock.ema20/maxValue)*100}%">
                    </div>
                </div>

                <p>EMA50 : ${stock.ema50}</p>

                <div class="bar">
                    <div class="fill ema50"
                    style="width:${(stock.ema50/maxValue)*100}%">
                    </div>
                </div>

                <p>EMA100 : ${stock.ema100}</p>

                <div class="bar">
                    <div class="fill ema100"
                    style="width:${(stock.ema100/maxValue)*100}%">
                    </div>
                </div>

                <p>EMA200 : ${stock.ema200}</p>

                <div class="bar">
                    <div class="fill ema200"
                    style="width:${(stock.ema200/maxValue)*100}%">
                    </div>
                </div>

            </div>
        `;

        const header = card.querySelector(".stock-header");
        const details = card.querySelector(".details");

        header.addEventListener("click", () => {

            if(details.style.display === "block"){
                details.style.display = "none";
            }
            else{
                details.style.display = "block";
            }

        });

        stockList.appendChild(card);

    });

}

loadData();
