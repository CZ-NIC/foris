// Render a chart based on table data
var make_chart = function() {
  var graph_config = {
    data: {
      datasets: [
        {
          lineTension: 0,
          label: Foris.sampleMessages.chartLabel,  // transaltions are defined within dynamic js
          data: graph_data,
        },
      ],
      fill: true,
    },
    options: {
      responsive: true,
      title: {
        display: true,
        text: Foris.sampleMessages.chartTitle  // transaltions are defined within dynamic js
      },
      tooltips: {
        mode: 'index',
        intersect: false,
      },
      hover: {
        mode: 'nearest',
        intersect: true
      },
      scales: {
        xAxes: [{
          display: false,
          scaleLabel: {
            display: true,
            labelString: Foris.sampleMessages.chartTimeAxis  // transaltions are defined within dynamic js
          }
        }],
        yAxes: [{
          display: true,
          ticks: {
            suggestedMin: 0,
            suggestedMax: 100,
          },
          scaleLabel: {
            display: true,
            labelString: Foris.sampleMessages.chartValueAxis  // transaltions are defined within dynamic js
          }
        }],
      },
    },
  };
  var graph_ctx = document.getElementById("canvas").getContext("2d");
  graph_config.options.scales.xAxes[0].ticks = {
      min: graph_config.data.datasets[0].data[0].x,
      max: graph_config.data.datasets[0].data[graph_config.data.datasets[0].data.length - 1].x,
  };
  Foris.lineChart = new Chart.Scatter(graph_ctx, graph_config);
  Foris.lineChartData = graph_config.data;
  Foris.lineChartOptions = graph_config.options;
}

// Global chart data
var graph_data;

// Functions which updates the chart
Foris.update_sample_chart = function() {
    // Clear current chart
    $("#canvas-container").empty();
    $("#canvas-container").append('<canvas id="canvas"></canvas>');

    // Set data
    graph_data = [];
    var idx = 0;
    $("#records-table td.table-index").each(function(idx, item) {
        graph_data[idx] = {x: parseInt($(item).text())};
        idx++;
    });
    idx = 0;
    $("#records-table td.table-value").each(function(idx, item) {
        graph_data[idx]["y"] = parseInt($(item).text());
        idx++;
    });

    // render chart
    make_chart();
}

// Update chart after page is rendred
$(document).ready(function() {
  Foris.update_sample_chart();
});
