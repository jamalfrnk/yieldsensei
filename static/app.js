// Market Intelligence Functions
    async function updateMarketIntelligence(symbol) {
        try {
            const response = await fetch(`/api/market-intelligence/${symbol}`);
            const data = await response.json();

            // Update sentiment chart
            const sentimentCtx = document.getElementById('sentimentChart').getContext('2d');
            new Chart(sentimentCtx, {
                type: 'gauge',
                data: {
                    datasets: [{
                        value: data.sentiment.score * 100,
                        minValue: 0,
                        maxValue: 100,
                        backgroundColor: ['#ef4444', '#f97316', '#22c55e']
                    }]
                }
            });

            // Update sentiment factors
            const factorsDiv = document.getElementById('sentimentFactors');
            factorsDiv.innerHTML = data.sentiment.factors
                .map(factor => `<p>• ${factor}</p>`)
                .join('');

            // Update volume metrics
            document.getElementById('volume24h').textContent = 
                new Intl.NumberFormat('en-US', {
                    style: 'currency',
                    currency: 'USD'
                }).format(data.volume.total_24h);

            document.getElementById('volumeChange').textContent = 
                `${data.volume.change_24h > 0 ? '+' : ''}${data.volume.change_24h.toFixed(2)}%`;
        } catch (error) {
            console.error('Error updating market intelligence:', error);
            showNotification('Failed to update market intelligence', 'error');
        }
    }

    // Initialize market intelligence on load
    const urlParams = new URLSearchParams(window.location.search);
    const symbol = urlParams.get('symbol');
    if (symbol) {
        updateMarketIntelligence(symbol);
    }