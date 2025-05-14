$(document).ready(function() { // Ensures jQuery and DOM are ready
    const fighterSelect1 = $('#fighter-select1');
    const fighterSelect2 = $('#fighter-select2');
    const viewChartBtn = $('#view-chart-btn');
    const clearChartBtn = $('#clear-chart-btn');
    const ctx = document.getElementById('eloChart').getContext('2d');
    let eloChart;

    const lineColors = ['#bb86fc', '#03dac6', '#cf6679', '#f48fb1']; // Purple, Teal, Red, Pink

    // Initialize Select2
    $('.fighter-select').select2({
        placeholder: "-- Select Fighter --",
        allowClear: true
    });

    // Populate Fighter Dropdowns
    fetch('/api/fighters')
        .then(response => response.json())
        .then(fighters => {
            fighters.forEach(fighter => {
                const option = new Option(fighter.name, fighter.id, false, false);
                // Append to both, Select2 will handle the rest
                fighterSelect1.append(option.cloneNode(true));
                fighterSelect2.append(option.cloneNode(true));
            });
            // Trigger change for Select2 to update (if options added after init)
            fighterSelect1.trigger('change');
            fighterSelect2.trigger('change');
        })
        .catch(error => console.error('Error fetching fighters:', error));

    async function fetchFighterEloData(fighterId) {
        if (!fighterId) return null;
        try {
            const response = await fetch(`/api/elo_history/${fighterId}`);
            if (!response.ok) {
                console.error(`Error fetching ELO for fighter ${fighterId}: ${response.statusText}`);
                const errorData = await response.json();
                alert(`Error for fighter ID ${fighterId}: ${errorData.error || response.statusText}`);
                return null;
            }
            return await response.json();
        } catch (error) {
            console.error(`Network error fetching ELO for fighter ${fighterId}:`, error);
            alert(`Network error for fighter ID ${fighterId}. Check console.`);
            return null;
        }
    }

    viewChartBtn.on('click', async () => {
        const fighterId1 = fighterSelect1.val();
        const fighterId2 = fighterSelect2.val();

        if (!fighterId1 && !fighterId2) {
            alert('Please select at least one fighter.');
            return;
        }
         if (fighterId1 && fighterId2 && fighterId1 === fighterId2) {
            alert("Please select two different fighters for comparison, or clear one selection.");
            return;
        }


        let datasets = [];
        let chartTitleFighters = [];

        if (fighterId1) {
            const data1 = await fetchFighterEloData(fighterId1);
            if (data1 && data1.data.length > 0) {
                datasets.push({
                    label: data1.fighter_name,
                    data: data1.labels.map((label, index) => ({ x: label, y: data1.data[index] })),
                    borderColor: lineColors[0],
                    backgroundColor: lineColors[0] + '20', // Lighter fill
                    fill: false, // or 'origin' or true for filled area
                    tension: 0.1,
                    pointRadius: 3,
                    pointHoverRadius: 5
                });
                chartTitleFighters.push(data1.fighter_name);
            } else if (data1 && data1.data.length === 0) {
                alert(`No ELO history found for ${data1.fighter_name || 'Fighter 1'}. They might be new or have no recorded fights yet.`);
            }
        }

        if (fighterId2) {
            const data2 = await fetchFighterEloData(fighterId2);
            if (data2 && data2.data.length > 0) {
                 datasets.push({
                    label: data2.fighter_name,
                    data: data2.labels.map((label, index) => ({ x: label, y: data2.data[index] })),
                    borderColor: lineColors[1],
                    backgroundColor: lineColors[1] + '20',
                    fill: false,
                    tension: 0.1,
                    pointRadius: 3,
                    pointHoverRadius: 5
                });
                chartTitleFighters.push(data2.fighter_name);
            } else if (data2 && data2.data.length === 0) {
                 alert(`No ELO history found for ${data2.fighter_name || 'Fighter 2'}. They might be new or have no recorded fights yet.`);
            }
        }

        if (datasets.length === 0 && (fighterId1 || fighterId2)) {
            // This case might occur if fetchFighterEloData returned null for all selected fighters
            alert("Could not fetch ELO data for the selected fighter(s). Check console for errors.");
            return;
        }


        if (eloChart) {
            eloChart.destroy();
        }

        eloChart = new Chart(ctx, {
            type: 'line',
            data: { datasets: datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'year', // Auto adapts, or specify: 'day', 'month', 'year'
                            tooltipFormat: 'MMM dd, yyyy',
                            displayFormats: {
                                millisecond: 'HH:mm:ss.SSS',
                                second: 'HH:mm:ss',
                                minute: 'HH:mm',
                                hour: 'HH',
                                day: 'MMM dd',
                                week: 'll',
                                month: 'MMM yyyy',
                                quarter: '[Q]Q - yyyy',
                                year: 'yyyy'
                            }
                        },
                        title: { display: true, text: 'Date', color: '#e0e0e0' },
                        ticks: { color: '#e0e0e0' },
                        grid: { color: '#444444' }
                    },
                    y: {
                        title: { display: true, text: 'Elo Rating', color: '#e0e0e0' },
                        ticks: { color: '#e0e0e0', beginAtZero: false }, // Elo rarely starts at 0
                        grid: { color: '#444444' }
                    }
                },
                plugins: {
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: '#2c2c2c',
                        titleColor: '#bb86fc',
                        bodyColor: '#e0e0e0',
                        borderColor: '#444',
                        borderWidth: 1
                    },
                    legend: {
                        position: 'top',
                        labels: { color: '#e0e0e0' }
                    },
                    title: {
                        display: true,
                        text: chartTitleFighters.length > 0 ? chartTitleFighters.join(' vs ') + ' ELO Progression' : 'Select Fighter(s) to View ELO',
                        color: '#e0e0e0',
                        font: { size: 16 }
                    }
                }
            }
        });
    });

    clearChartBtn.on('click', () => {
        if (eloChart) {
            eloChart.destroy();
            eloChart = null;
        }
        fighterSelect1.val(null).trigger('change'); // Clear Select2 selection
        fighterSelect2.val(null).trigger('change'); // Clear Select2 selection
    });
});