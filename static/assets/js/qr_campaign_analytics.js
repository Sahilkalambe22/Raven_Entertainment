function initQrCampaignAnalytics() {
  function loadQrCampaignCharts(filters = {}) {
    let url = "/accounts/get_qr_marketing_data/";
    let params = new URLSearchParams(filters).toString();
    if (params) url += "?" + params;

    fetch(url)
      .then(res => res.json())
      .then(data => {
        const labels = data.map(item => item.identifier);
        const values = data.map(item => item.count);
        const total = values.reduce((sum, val) => sum + val, 0);

        if (window.qrBarChart) window.qrBarChart.destroy();
        if (window.qrPieChart) window.qrPieChart.destroy();

        window.qrBarChart = new Chart(document.getElementById("qrCampaignBarChart").getContext("2d"), {
          type: "bar",
          data: {
            labels: labels,
            datasets: [{
              label: "QR Scans by Source",
              data: values,
              backgroundColor: "#ff9f40",
              borderColor: "#fff",
              borderWidth: 1
            }]
          },
          options: {
            responsive: true,
            plugins: {
              legend: { display: false },
              tooltip: { enabled: true },
              datalabels: {
                anchor: 'end',
                align: 'top',
                color: '#f5f5f5',
                font: { weight: 'bold' }
              }
            },
            scales: {
              y: {
                beginAtZero: true,
                ticks: { color: '#f5f5f5' },
                title: { display: true, text: 'Scan Count', color: '#f5f5f5' }
              },
              x: {
                ticks: { color: '#f5f5f5' },
                title: { display: true, text: 'Source Identifier', color: '#f5f5f5' }
              }
            }
          },
          plugins: [ChartDataLabels]
        });

        window.qrPieChart = new Chart(document.getElementById("qrCampaignPieChart").getContext("2d"), {
          type: "pie",
          data: {
            labels: labels,
            datasets: [{
              data: values,
              backgroundColor: ["#e74c3c", "#8e44ad"]
            }]
          },
          options: {
            plugins: {
              legend: { labels: { color: '#f5f5f5' } },
              tooltip: {
                callbacks: {
                  label: context => {
                    const value = context.raw;
                    const percentage = ((value / total) * 100).toFixed(1);
                    return `${context.label}: ${percentage}% (${value} scans)`;
                  }
                }
              },
              datalabels: {
                color: '#fff',
                font: { weight: 'bold' },
                formatter: value => `${((value / total) * 100).toFixed(1)}%`
              }
            }
          },
          plugins: [ChartDataLabels]
        });

        window.qrCampaignData = data;
      });
  }

  loadQrCampaignCharts();

  document.getElementById("qrCampaignFilterBtn").addEventListener("click", () => {
    const filters = {
      start_date: document.getElementById("startDate").value,
      end_date: document.getElementById("endDate").value,
      city: document.getElementById("city").value
    };
    loadQrCampaignCharts(filters);
  });

  document.getElementById("downloadCSV").addEventListener("click", () => {
    const data = window.qrCampaignData || [];
    if (!data.length) return alert("No data to export.");
    const headers = ["Identifier", "Scan Count"];
    const csvContent = [headers.join(","), ...data.map(item => `${item.identifier},${item.count}`)].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "qr_campaign_data.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  });

  document.getElementById("downloadPDF").addEventListener("click", async () => {
    const data = window.qrCampaignData || [];
    if (!data.length) return alert("No data to export.");
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    doc.setFontSize(16);
    doc.text("QR Campaign Analytics", 20, 20);
    doc.setFontSize(12);
    doc.text("Identifier        Count", 20, 35);
    let y = 45;
    data.forEach(item => {
      doc.text(`${item.identifier.padEnd(15)} ${item.count}`, 20, y);
      y += 10;
    });
    doc.save("qr_campaign_data.pdf");
  });
}
