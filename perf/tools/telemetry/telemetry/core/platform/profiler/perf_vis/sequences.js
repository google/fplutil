
var legend_width = document.getElementById("sidebar").clientWidth;

// Area excluding the legend.
var body_width = document.body.clientWidth - legend_width;
var body_height = document.body.clientHeight;

// Dimensions of sunburst element.
var chart_element = document.getElementById("chart");
var chart_width = chart_element.clientWidth;
var chart_height = chart_element.clientHeight;
var chart_radius = Math.min(chart_width, chart_height) * 0.85;
var chart_diameter = chart_radius * 2;
var chart_center_radius = chart_radius / 8;
var chart_center_x = chart_radius / 2 + legend_width;
var chart_center_y = chart_radius / 2 * 1.3;

// Dimensions of the stack trace when mousing over the sunburst.
var sequence_element = document.getElementById("sequence");
var sequence_width = sequence_element.clientWidth;
var sequence_height = sequence_element.clientHeight;

// Set the position of the explanation element in the center of the chart.
var explanation_element = document.getElementById("explanation");
var explanation_style = explanation_element.style;
var explanation_size = chart_center_radius;
explanation_style.position = "absolute";
explanation_style.width = explanation_size + "px";
explanation_style.height = explanation_size + "px";
explanation_style.left = (chart_center_x - (explanation_size * 0.75)) + "px";
explanation_style.top = (chart_center_y - (explanation_size * 0.40)) + "px";
explanation_style.fontSize = (explanation_size / 5) + "px";

// Breadcrumb dimensions: width, height, spacing, width of tip/tail.
var b = {
  w: sequence_width, h: 16, s: 1, t: 10
};

// Mapping of step names to colors.
var colors = {
  "Chrome": "#5687d1",
  "Kernel": "#7b615c",
  "GPU Driver": "#ff0000",
  "Java": "#de783b",
  "Android": "#6ab975",
  "Thread": "#aaaaaa",
  "Standard Lib": "#bbbbbb",
  "<self>": "#888888",
  "<unknown>": "#444444"
};

// Total size of all segments; we set this later, after loading the data.
var totalSize = 0; 

/*
var x = d3.scale.linear()
    .range([0, 2 * Math.PI]);

var y = d3.scale.sqrt()
    .range([50, radius*1.5]);

var partition = d3.layout.partition()
    .size([1, 1]) // radius * radius
    .value(function(d) { return d.size; });

var arc = d3.svg.arc()
    .startAngle(function(d) { return Math.max(0, Math.min(2 * Math.PI, x(d.x))); })
    .endAngle(function(d) { return Math.max(0, Math.min(2 * Math.PI, x(d.x + d.dx))); })
    .innerRadius(function(d) { return Math.max(0, y((d.y))); })
    .outerRadius(function(d) { return Math.max(0, y((d.y + d.dy))); });
*/

createVisualization(json);

clickedY = 0;
var min_x = 0.0;
var max_x = 1.0;
var min_y = 0.0;

// Main function to draw and set up the visualization, once we have the data.
function createVisualization(json) {

  // Basic setup of page elements.
  initializeBreadcrumbTrail();
  drawLegend();

  var vis = d3.select("#chart").append("svg:svg")
      .attr("width", chart_diameter)
      .attr("height", chart_diameter)
      .append("svg:g")
      .attr("id", "container")
      .attr("transform", "translate(" + chart_center_x +
            "," + chart_center_y + ")");

  var clickedNode = null;
  var click_stack = new Array();
  click_stack.push(0);

  function zoomout(d) {
    if (click_stack.length > 1)
      click_stack.pop();
    location.hash = click_stack[click_stack.length-1];
  }
  // Bounding circle underneath the sunburst, to make it easier to detect
  // when the mouse leaves the parent g.
  vis.append("svg:circle")
      .attr("r", chart_radius)
      .style("opacity", 0)
      .on("click", zoomout);

  // For efficiency, filter nodes to keep only those large enough to see.
  //var nodes = partition.nodes(json);
  //nodes.forEach(function f(d, i) { d.id = i; })
  //totalSize = nodes[0].value; //path.node().__data__.value;

  ///////////////////////
  var partition = d3.layout.partition()
    .size([1, 1]) // radius * radius
    .value(function(d) { return d.size; });
  var nodes = partition.nodes(json);
  nodes.forEach(function f(d, i) { d.id = i; });
  var totalSize = nodes[0].value;
  var depth = 1.0 + d3.max(nodes, function(d) { return d.depth; });
  var yDomainMin = 1.0 / depth;
  var yDomainMax = yDomainMin + yDomainMin * 40; //Math.min(Math.max(depth, 20), 50) / depth;

  var x = d3.scale.linear()
      .range([0, 2 * Math.PI]);

  var y = d3.scale.sqrt()
      .domain([yDomainMin, yDomainMax])
      .range([chart_center_radius, chart_radius]);

  var arc = d3.svg.arc()
      .startAngle(function(d) {
        return Math.max(0, Math.min(2 * Math.PI, x(d.x)));
      })
      .endAngle(function(d) {
        return Math.max(0, Math.min(2 * Math.PI, x(d.x + d.dx)));
      })
      .innerRadius(function(d) { return Math.max(0, y((d.y))); })
      .outerRadius(function(d) { return Math.max(0, y((d.y + d.dy))); });

  // Interpolate the scales!
  function arcTween(minX, maxX, minY) {
    var xd, yd, yr;

    if (minY > 0) {
      xd = d3.interpolate(x.domain(), [minX, maxX]);
      yd = d3.interpolate(y.domain(), [minY, minY + yDomainMin * 40]);
      yr = d3.interpolate(y.range(), [chart_center_radius, chart_radius]);
    }
    else {
      xd = d3.interpolate(x.domain(), [minX, maxX]);
      yd = d3.interpolate(y.domain(), [yDomainMin, yDomainMin + yDomainMin * 40]);
      yr = d3.interpolate(y.range(), [chart_center_radius, chart_radius]);
    }

    return function(d, i) {
      return i ? function(t) { return arc(d); }
          : function(t) {
            x.domain(xd(t)); y.domain(yd(t)).range(yr(t)); return arc(d);
          };
    };
  }

  function getNode(id) {
    for (var i = 0; i < nodes.length; i++) {
      if (nodes[i].id == id)
        return nodes[i];
    }
    return null;
  }

  var entityMap = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': '&quot;',
    "'": '&#39;',
    "/": '&#x2F;'
  };

  function escapeHtml(string) {
    return String(string).replace(/[&<>"'\/]/g, function (s) {
      return entityMap[s];
    });
  }

  function zoomto(id) {
    var d = getNode(id);

    if (d) {
      clickedY = d.y;
      min_x = d.x;
      max_x = d.x + d.dx;
      min_y = d.y;
    }
    else {
      clickedY = -1;
      min_x = 0.0;
      max_x = 1.0;
      min_y = 0.0;
    }

    clickedNode = d;
    redraw(min_x, max_x, min_y);
    var path = vis.selectAll("path");
    
    path.transition()
      .duration(750)
      .attrTween("d", arcTween(min_x, max_x, min_y));

    showBreadcrumbs(d);

    var summary = '';
    summary += '<b>' + d.value.toFixed(3) + 'ms ' + escapeHtml(d.name) + '</b>';
    d.children.forEach(function f(c, i) {
      summary += '<br> > <b>' + c.value.toFixed(3) + 'ms ' + (100 * c.value / d.value).toFixed(3) + '% ' 
        + '<a href=\"#'+c.id + '\">' + escapeHtml(c.name) + '</a></b>';
    });
    d3.select("#summary")
        .html(summary);
  }

  function click(d) {
    if (d3.event.shiftKey) {
      // Zoom partially onto the selected range
      var diff_x = (max_x - min_x) * 0.5;
      min_x = d.x + d.dx * 0.5 - diff_x * 0.5;
      min_x = min_x < 0.0 ? 0.0 : min_x;
      max_x = min_x + diff_x;
      max_x = max_x > 1.0 ? 1.0 : max_x;
      min_x = max_x - diff_x;

      redraw(min_x, max_x, min_y);

      var path = vis.selectAll("path");

      clickedNode = d;
      path.transition()
        .duration(750)
        .attrTween("d", arcTween(min_x, max_x, min_y));

      return;
    }

    if (click_stack[click_stack.length-1] != d.id) {
      click_stack.push(d.id);
      location.hash = d.id;
    }
  }

  // Restore everything to full opacity when moving off the visualization.
  function mouseleave(d) {
    // Hide the breadcrumb trail
    if (clickedNode != null)
      showBreadcrumbs(clickedNode);
    else {
      d3.select("#trail")
          .style("visibility", "hidden");

      // Deactivate all segments during transition.
      d3.selectAll("path").on("mouseover", null);

      // Transition each segment to full opacity and then reactivate it.
      d3.selectAll("path")
          .transition()
          .duration(300)
          .style("opacity", 1)
          .each("end", function() {
                  d3.select(this).on("mouseover", mouseover);
                });
      d3.select("#explanation")
          .transition()
          .duration(300)
          .style("visibility", "hidden");
    }
  }

  function redraw(min_x, max_x, min_y) {
    var scale = max_x - min_x;
    var visible_nodes = nodes.filter(function(d) {
        return d.depth && 
               (d.y >= min_y) &&
               (d.x < max_x) &&
               (d.x + d.dx > min_x) &&
               (d.dx / scale > 0.001); // 0.005 radians = 0.29 degrees
      });
    var path = vis.data([json]).selectAll("path")
      .data(visible_nodes, function(d) { return d.id; });

    path.enter().insert("svg:path")
      //.attr("display", function(d) { return d.depth ? null : "none"; })
      .attr("d", arc)
      .attr("fill-rule", "evenodd")
      .style("fill", function(dd) { return colors[dd.comp]; })
      .style("opacity", 0.7)
      .on("mouseover", mouseover)
      .on("click", click);

    path.exit().remove();
    return path;
  }

  //Interpolate the scales!
  /*
  function arcTween(minX, maxX, minY) {
    var xd, yd, yr;

    if (minY > 0) {
      xd = d3.interpolate(x.domain(), [minX, maxX]);
      yd = d3.interpolate(y.domain(), [minY, yDomainMax]);
      yr = d3.interpolate(y.range(), [chart_center_radius, chart_radius]);
    }
    else {
      xd = d3.interpolate(x.domain(), [minX, maxX]);
      yd = d3.interpolate(y.domain(), [yDomainMin, yDomainMax]);
      yr = d3.interpolate(y.range(), [chart_center_radius, chart_radius]);
    }

    return function(d, i) {
      return i ? function(t) { return arc(d); }
          : function(t) {
            x.domain(xd(t)); y.domain(yd(t)).range(yr(t)); return arc(d);
          };
    };
  }
  */

  function showBreadcrumbs(d) {
    var scale = max_x - min_x;
    var percentage = (100 * d.dx / scale).toPrecision(3);
    var tot = d.value.toPrecision(3);
    var percentageString = percentage + "%";
    if (percentage < 0.1) {
      percentageString = "< 0.1%";
    }

    d3.select("#percentage")
        .text(tot + 'ms ' + percentageString);

    d3.select("#explanation")
        .style("visibility", "");

    var sequenceArray = getAncestors(d);
    updateBreadcrumbs(sequenceArray, percentageString);

    // Fade all the segments.
    d3.selectAll("path")
        .style("opacity", 0.7);

    // Then highlight only those that are an ancestor of the current segment.
    vis.selectAll("path")
        .filter(function(node) {
                  return (sequenceArray.indexOf(node) >= 0);
                })
        .style("opacity", 1);
  }
  // Fade all but the current sequence, and show it in the breadcrumb trail.
  function mouseover(d) {
    showBreadcrumbs(d);
  }

  // Given a node in a partition layout, return an array of all of its ancestor
  // nodes, highest first, but excluding the root.
  function getAncestors(node) {
    var path = [];
    var current = node;
    while (current.parent && path.length < 48) {
      path.unshift(current);
      current = current.parent;
    }
    return path;
  }

  function initializeBreadcrumbTrail() {
    // Add the svg area.
    var trail = d3.select("#sequence").append("svg:svg")
        .attr("width", sequence_width)
        .attr("height", sequence_height)
        .attr("id", "trail");
    // Add the label at the end, for the percentage.
    trail.append("svg:text")
      .attr("id", "endlabel")
      .style("fill", "#000");
  }

  // Generate a string that describes the points of a breadcrumb polygon.
  function breadcrumbPoints(d, i) {
    var points = [];
    points.push("0,0");
    points.push(b.w + ",0");
    points.push(b.w + b.t + "," + (b.h / 2));
    points.push(b.w + "," + b.h);
    points.push("0," + b.h);
    //if (i > 0) { // Leftmost breadcrumb; don't include 6th vertex.
      points.push(b.t + "," + (b.h / 2));
    //}
    return points.join(" ");
  }

  // Update the breadcrumb trail to show the current sequence and percentage.
  function updateBreadcrumbs(nodeArray, percentageString) {

    // Data join; key function combines name and depth (= position in sequence).
    var g = d3.select("#trail")
        .selectAll("g")
        .data(nodeArray, function(d) { return d.name + d.depth; });

    // Add breadcrumb and label for entering nodes.
    var entering = g.enter().append("svg:g");

    entering.append("svg:polygon")
        .attr("points", breadcrumbPoints)
        .style("fill", function(d) { return colors[d.comp]; });

    entering.append("svg:text")
        .attr("x", 15)
        .attr("y", b.h / 2)
        .attr("dy", "0.35em")
        .attr("text-anchor", "start")
        .text(function(d) { return d.name; });

    // Set position for entering and updating nodes.
    g.attr("transform", function(d, i) {
      return "translate(" + legend_width + ", " + i * (b.h + b.s) + ")";
    });

    // Remove exiting nodes.
    g.exit().remove();

    /*
    // Now move and update the percentage at the end.
    d3.select("#trail").select("#endlabel")
        .attr("x", 0.0)
        .attr("y", (nodeArray.length + 0.5) * (b.h + b.t))
        .attr("dy", "0.35em")
        .attr("text-anchor", "middle")
        .text(percentageString);
    */

    // Make the breadcrumb trail visible, if it's hidden.
    d3.select("#trail")
        .style("visibility", "");

  }

  function drawLegend() {

    // Dimensions of legend item: width, height, spacing, radius of rounded rect.
    var li = {
      w: legend_width, h: 30, s: 3, r: 3
    };

    var legend = d3.select("#legend").append("svg:svg")
        .attr("width", li.w)
        .attr("height", d3.keys(colors).length * (li.h + li.s));

    var g = legend.selectAll("g")
        .data(d3.entries(colors))
        .enter().append("svg:g")
        .attr("transform", function(d, i) {
                return "translate(0," + i * (li.h + li.s) + ")";
             });

    g.append("svg:rect")
        .attr("rx", li.r)
        .attr("ry", li.r)
        .attr("width", li.w)
        .attr("height", li.h)
        .style("fill", function(d) { return d.value; });

    g.append("svg:text")
        .attr("x", li.w / 2)
        .attr("y", li.h / 2)
        .attr("dy", "0.35em")
        .attr("text-anchor", "middle")
        .text(function(d) { return d.key; });
  }



  // Client-side routes    
  var app = Sammy(function() {
      this.get('#:id', function() {
          var id = parseInt(this.params.id);
          clickedNode = getNode(id);
          zoomto(id);
      });
  
      this.get('', function() { this.app.runRoute('get', '#0') });
  }).run();

  // Add the mouseleave handler to the bounding circle.
  d3.select("#container")
      .on("mouseleave", mouseleave)
      ;
 };

