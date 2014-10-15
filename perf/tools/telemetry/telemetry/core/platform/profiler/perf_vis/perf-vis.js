// Dimensions of sunburst.
var width = 800;
var height = 800;
var radius = Math.min(width, height) / 2;

// Breadcrumb dimensions: width, height, spacing, width of tip/tail.
var b = {
  w: 1600, h: 16, s: 1, t: 10
};

// Mapping of step names to colors.
var colors = {
  "Chrome": "#5687d1",
  "Kernel": "#7b615c",
  "GPU Driver": "#cc0000",
  "Java": "#de783b",
  "Android": "#6ab975",
  "Thread": "#aaaaaa",
  "Standard Lib": "#bbbbbb",
};

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

clickedY = 0;
var min_x = 0.0;
var max_x = 1.0;
var min_y = 0.0;

var childTable = null;
var bottomUpTable = null;

// attach the .equals method to Array's prototype to call it on any array
Array.prototype.equals = function (array) {
    // if the other array is a falsy value, return
    if (!array)
        return false;

    // compare lengths - can save a lot of time 
    if (this.length != array.length)
        return false;

    for (var i = 0, l=this.length; i < l; i++) {
        // Check if we have nested arrays
        if (this[i] instanceof Array && array[i] instanceof Array) {
            // recurse into the nested arrays
            if (!this[i].equals(array[i]))
                return false;       
        }           
        else if (this[i] != array[i]) { 
            // Warning - two different object instances will never be equal: {x:20} != {x:20}
            return false;   
        }           
    }       
    return true;
}

$(document).ready(function() {
    //$('#demo').html( '<table cellpadding="0" cellspacing="0" border="0" class="display" id="example"></table>' );

    //var myLayout = $('body').layout({ applyDefaultStyles: true });
    //myLayout.options.west.resizable = true;
    //myLayout.sizePane("west", 820);

    childTable = $('#example').dataTable( {
      "dom": '<"child_toolbar">frtip',
      "fnRowCallback": function( nRow ) {
        // column index starts with 0 and we check if cells[2] is null to be ultra safe
        if(nRow.cells[3]) nRow.cells[3].noWrap = true;
        return nRow;
      },
      "scrollY": "280",
      "scrollX": true,
      "bAutoWidth": false,
      "paging":  false,
      "info":    false,
      "order": [[ 2, "desc" ]],
      "columns": [
          { "title": "", "sClass": "center", "width": "15px" },
          { "title": "Time", "sClass": "right", "width": "30px" },
          { "title": "Percent", "sClass": "right", "width": "30px" },
          { "title": "Method" }
      ]
    });

    $("div.child_toolbar").html('<b>Cellees:</b>');

    bottomUpTable = $('#bottom-up').dataTable( {
      "dom": '<"bottomup_toolbar">frtip',
      "fnRowCallback": function( nRow ) {
        // column index starts with 0 and we check if cells[2] is null to be ultra safe
        if(nRow.cells[3]) nRow.cells[3].noWrap = true;
        return nRow;
      },
      "scrollY": "280",
      "scrollX": true,
      "bAutoWidth": false,
      "paging":  false,
      "info":    false,
      "order": [[ 2, "desc" ]],
      "columns": [
          { "title": "", "sClass": "center", "width": "15px" },
          { "title": "Time (Incl)", "sClass": "right", "width": "30px" },
          { "title": "Time (Self)", "sClass": "right", "width": "30px" },
          { "title": "Call Sites", "sClass": "right", "width": "30px" },
          { "title": "Method" }
      ]
    });

    $("div.bottomup_toolbar").html('<b>All methods:</b>');

    createVisualization(json);
} );

// Main function to draw and set up the visualization, once we have the data.
function createVisualization(json) {

  var legendText = undefined;
  // Basic setup of page elements.
  initializeBreadcrumbTrail();
  //drawLegend();

  var vis = d3.select("#chart").append("svg:svg")
      .attr("width", width)
      .attr("height", height)
      .append("svg:g")
      .attr("id", "container")
      .attr("transform", "translate(" + width / 2 + "," + height / 2 + ")");

  var clickedNode = null;
  var click_stack = new Array();
  click_stack.push({
    id: 0,
  });

  function zoomout(d) {
    if (click_stack.length > 1) {
      click_stack.pop();
      var hash = click_stack[click_stack.length - 1];
      click_stack.pop();
      location.hash = JSON.stringify(hash);
    }
  }

  // Bounding circle underneath the sunburst, to make it easier to detect
  // when the mouse leaves the parent g.
  vis.append("svg:circle")
      .attr("r", radius)
      .style("opacity", 0)
      .on("click", zoomout);

  // For efficiency, filter nodes to keep only those large enough to see.
  //var nodes = partition.nodes(json);
  //nodes.forEach(function f(d, i) { d.id = i; })

  /*
    $(document).ready(function() {
        $('#example').dataTable( {
            "scrollY": 200,
            "scrollX": true,
            "paging":   false,
            "info":     false
        } );
    } );
  */

  json.comp = 'Thread';
  var stackIdToNode = {};
  var stackIdCounter = 0;
  function setNodeIds(node) {
    node.stackId = stackIdCounter++;
    stackIdToNode[node.stackId] = node;
    if (node.children) {
      d3.values(node.children).forEach(function f(c, i) {
        setNodeIds(c);
      });
    }
  }
  setNodeIds(json);

  var nodes = undefined;
  var yDomainMin = undefined;
  var yDomainMax = undefined;
  var xScaler = undefined;
  var yScaler = undefined;
  var arc = undefined;
  var arcTween = undefined;
  var currSelection = {stack: [], hide: [], id: -1};

  function initPartition(data) {
    ///////////////////////
    var partition = d3.layout.partition()
      .size([1, 1]) // radius * radius
      .value(function(d) { return d.size; });
    nodes = partition.nodes(data);
    nodes.forEach(function f(node, i) {
      node.id = i;
    });

    var depth = 1.0 + d3.max(nodes, function(d) { return d.depth; });
    yDomainMin = 1.0 / depth;
    yDomainMax = yDomainMin + yDomainMin * 40; //Math.min(Math.max(depth, 20), 50) / depth;

    xScaler = d3.scale.linear()
      .range([0, 2 * Math.PI]);

    yScaler = d3.scale.sqrt()
        .domain([yDomainMin, yDomainMax])
        .range([50, radius]);

    arc = d3.svg.arc()
      .startAngle(function(d) {
        return Math.max(0, Math.min(2 * Math.PI, xScaler(d.x)));
      })
      .endAngle(function(d) {
        return Math.max(0, Math.min(2 * Math.PI, xScaler(d.x + d.dx)));
      })
      .innerRadius(function(d) { return Math.max(0, yScaler((d.y))); })
      .outerRadius(function(d) { return Math.max(0, yScaler((d.y + d.dy))); });

    // Interpolate the scales!
    arcTween = function (minX, maxX, minY) {
      var xd, yd, yr;

      if (minY > 0) {
        xd = d3.interpolate(xScaler.domain(), [minX, maxX]);
        yd = d3.interpolate(yScaler.domain(), [minY, minY + yDomainMin * 40]);
        yr = d3.interpolate(yScaler.range(), [50, radius]);
      }
      else {
        xd = d3.interpolate(xScaler.domain(), [minX, maxX]);
        yd = d3.interpolate(yScaler.domain(), [yDomainMin, yDomainMin + yDomainMin * 40]);
        yr = d3.interpolate(yScaler.range(), [50, radius]);
      }

      return function(d, i) {
        return i ? function(t) { return arc(d); }
            : function(t) {
              xScaler.domain(xd(t)); yScaler.domain(yd(t)).range(yr(t)); return arc(d);
            };
      };
    }
  }

  initPartition(json);

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

  function zoomto(args) {
    if (!currSelection ||
        !currSelection.stack.equals(args.stack) ||
        !currSelection.ignore.equals(args.ignore) ||
        !currSelection.hide.equals(args.hide) ||
        currSelection.merged != args.merged) {
      // Clear old path
      var path = vis.selectAll("path")
        .data([]);
      path.exit().remove();
      currSelection = args;
      drawLegend();

      var mergingDiv = d3.select("#merging");

      if (args.stack.length > 1) {
        var newSelectionA = jQuery.extend(true, {}, args);
        var newSelectionB = jQuery.extend(true, {}, args);
        newSelectionA.merged = !newSelectionA.merged;
        newSelectionA.id = 1;
        newSelectionB.merged = false;
        newSelectionB.id = 1;
        newSelectionB.stack = [0];
        mergingDiv.html(
            "<b>Multiple Selection: " + (args.merged ? 'Merged' : 'Filtered') + " View</b><br>" +
            "<a href='#" + escapeHtml(JSON.stringify(newSelectionB)) + "'>Clear Multiple Selection</a><br>" +
            "<a href='#" + escapeHtml(JSON.stringify(newSelectionA)) + "'>Switch to " +
            (args.merged ? 'Filtered' : 'Merged') + ' View</a>');
      }
      else {
        mergingDiv.html('');
      }

      // init data
      var rootNode = null;
      if (args.stack.length < 0) {
        rootNode = stackIdToNode[args.stack[0]];
      } else {
        function mergeChild(into, node, inFilter, outFilter) {
          // node is a single node to merge
          // into is an array to merge to
          if (!inFilter)
            inFilter = args.stack.indexOf(node.stackId) >= 0;
          
          // Hide these stacks.
          if (args.hide.indexOf(node.stackId) >= 0)
            outFilter = false;

          if (args.ignore.indexOf(node.comp) >= 0)
            return;
          var toNode = undefined;
          for (var i = 0; i < into.length; i++) {
            var child = into[i];
            if (node.name == child.name && node.comp == child.comp) {
              toNode = child;
              break;
            }
          }
          if (!toNode) {
            toNode = {comp: node.comp, name: node.name, stackIds: []};
            into.push(toNode);
          }

          toNode.stackIds.push(node.stackId);

          if (node.size && args.ignore.indexOf(node.comp) < 0 && inFilter && outFilter) {
            if (!toNode.size)
              toNode.size = node.size;
            else
              toNode.size += node.size;
          }

          if (node.children) {
            if (!toNode.children)
              toNode.children = []
            for (var i = 0; i < node.children.length; i++) {
              mergeChild(toNode.children, node.children[i], inFilter, outFilter);
            }
          }
        }

        rootNode = {comp: 'root', name: 'root', children: [], stackIds: []};
        var mergeInto;
        if (args.stack.length <= 1 || true) {
          mergeInto = rootNode.children;
        } else {
          rootNode.children.push({
            comp: 'Thread',
            children: [],
            stackIds: args.stack,
            name: '<Multiple Selection: ' + args.stack.length + ' * ' +
                stackIdToNode[args.stack[0]].name + '>'
          });
          mergeInto = rootNode.children[0].children;
        }

        if (args.merged) {
          for (var i = 0; i < args.stack.length; i++) {
            mergeChild(mergeInto, stackIdToNode[args.stack[i]], false, true);
          }
        }
        else {
          mergeChild(mergeInto, stackIdToNode[0], false, true);
        }

        function fixSelfTimes(node) {
          if (node.children) {
            for (var i = 0; i < node.children.length; i++) {
              if (node.children[i].name == '<self>') {
                if (node.size) {
                  node.children[i].size += node.size;
                  node.size = undefined;
                }
              } else {
                fixSelfTimes(node.children[i]);
              }
            }
            if (node.size) {
              node.children.push({comp: node.comp, name: '<self>', size: node.size});
              node.size = undefined;
            }
          }
        }
        fixSelfTimes(rootNode);
      }
      initPartition(rootNode);
    }
    currSelection = args;
    click_stack.push(currSelection);

    var d = getNode(args.id);

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


    /*
    var summary = '';
    summary += '<b>' + d.value.toFixed(3) + 'ms ' + escapeHtml(d.name) + '</b>';
    d.children.forEach(function f(c, i) {
      summary += '<br> > <b>' + c.value.toFixed(3) + 'ms ' + (100 * c.value / d.value).toFixed(3) + '% '
        + '<a href=\"#'+c.id + '\">' + escapeHtml(c.name) + '</a></b>';
    });
    d3.select("#summary")
        .html(summary);
    */

    var dataSet = [];
    if (d.children) {
      d.children.forEach(function f(c, i) {
        if (c.value == 0)
          return;
        var newSelection = jQuery.extend(true, {}, currSelection);
        newSelection.id = c.id;
        var hideSelection = jQuery.extend(true, {}, currSelection);
        hideSelection.hide = hideSelection.hide.concat(c.stackIds);

        dataSet.push([
          '<a href=\"#'+escapeHtml(JSON.stringify(hideSelection)) + '\">hide</a>',
          c.value.toFixed(3) + 'ms',
          (100 * c.value / d.value).toFixed(3) + '%',
          '<a href=\"#'+escapeHtml(JSON.stringify(newSelection)) + '\">' + escapeHtml(c.name) + '</a>'
        ]);
      });
    } else {
      dataSet.push(['', '', 'No data.']);
    }


    
    childTable.fnClearTable();
    childTable.fnFilter('');
    childTable.fnAddData(dataSet);
    childTable.fnDraw();

    dataSet = [];
    if (d.stackIds[0] > 0) {
      var allFrames = {};
      function procNode(node) {
        var currFrame;
        if (node.id != 0) {
          if (!(node.name in allFrames))
            allFrames[node.name] = {self: 0.0, total: 0.0, stacks: [], mark: 0};
          currFrame = allFrames[node.name];
          if (currFrame.mark == 0) {
            currFrame.total += node.value;
            for (var i = 0; i < node.stackIds.length; i++) {
              currFrame.stacks.push(node.stackIds[i]);
            }
          }
        } else {
          currFrame = {mark: 0};
        }
        
        currFrame.mark++;
        if (node.children) {
          node.children.forEach(function f(c, i) {
            if (c.name == '<self>')
              currFrame.self += c.value;
            else
              procNode(c);
          });
        } else {
          currFrame.self += node.value;
        }
        currFrame.mark--;
      }
      procNode(d);

      d3.entries(allFrames).forEach(function (f) {
        if (f.value.total < 0.0005)
          return;
        var mergedSelection = jQuery.extend(true, {}, currSelection);
        mergedSelection.stack = f.value.stacks;
        mergedSelection.id = 0;
        mergedSelection.merged = true;

        var hideSelection = jQuery.extend(true, {}, currSelection);
        hideSelection.hide = hideSelection.hide.concat(f.value.stacks);

        dataSet.push([
          '<a href=\"#'+escapeHtml(JSON.stringify(hideSelection)) + '\">hide</a>',
          f.value.total.toFixed(3),
          f.value.self.toFixed(3),
          f.value.stacks.length,
          '<a href=\"#'+escapeHtml(JSON.stringify(mergedSelection)) + '\">' + escapeHtml(f.key) + '</a>'
          ]);
      });
    }
    else {
      dataSet.push(['', '', '', '', 'Please select a method or thread.']);
    }

    bottomUpTable.fnClearTable();
    bottomUpTable.fnFilter('');
    bottomUpTable.fnAddData(dataSet);
    bottomUpTable.fnDraw();
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
      var newSelection = jQuery.extend(true, {}, currSelection);
      newSelection.id = d.id;
      location.hash = JSON.stringify(newSelection);
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
    var path = vis.selectAll("path")
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
    while (current.parent && path.length < 22) {
      path.unshift(current);
      current = current.parent;
    }
    return path;
  }

  function initializeBreadcrumbTrail() {
    // Add the svg area.
    var trail = d3.select("#sequence").append("svg:svg")
        .attr("width", 1200)
        .attr("height", 400)
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
      return "translate(0, " + i * (b.h + b.s) + ")";
    });

    // Remove exiting nodes.
    g.exit().remove();

    // Make the breadcrumb trail visible, if it's hidden.
    d3.select("#trail")
        .style("visibility", "");

  }

  function legendClick(d) {
    var newSelection = jQuery.extend(true, {}, currSelection);
    var i = newSelection.ignore.indexOf(d.key);
    if (i >= 0)
      newSelection.ignore.splice(i, 1);
    else
      newSelection.ignore.push(d.key);
    location.hash = JSON.stringify(newSelection);
  }

  function drawLegend() {

    // Dimensions of legend item: width, height, spacing, radius of rounded rect.
    var li = {
      w: 75, h: 30, s: 3, r: 3
    };

    d3.select("#legend").selectAll('svg').remove();

    var legend = d3.select("#legend").append("svg:svg")
        .attr("width", li.w)
        .attr("height", d3.keys(colors).length * (li.h + li.s));

    var legendGroup = legend.selectAll("g")
        .data(d3.entries(colors))
        .enter().append("svg:g")
        .on("click", legendClick)
        .attr("transform", function(d, i) {
                return "translate(0," + i * (li.h + li.s) + ")";
             });

    legendText = legendGroup.append("svg:rect")
        .attr("rx", li.r)
        .attr("ry", li.r)
        .attr("width", li.w)
        .attr("height", li.h)
        .style("fill", function(d) { return d.value; });


    legendGroup.append("svg:text")
        .attr("x", li.w / 2)
        .attr("y", li.h / 2)
        .attr("dy", "0.35em")
        .attr("text-anchor", "middle")
        .style("text-decoration", function(d) {
          return (currSelection.ignore.indexOf(d.key) >= 0) ? 'line-through' : '';
        })
        .text(function(d) { return d.key; });
  }



  // Client-side routes
  var app = Sammy(function() {
      this.get('#:args', function() {
          var args = jQuery.parseJSON(this.params.args);
          if (!args.stack)
            args.stack = [0];
          if (typeof args.merged === 'undefined')
            args.merged = false;
          if (!args.id)
            args.id = 1;
          if (!args.ignore)
            args.ignore = [];
          if (!args.hide)
            args.hide = [];

          clickedNode = getNode(args.id);
          zoomto(args);
      });

      this.get('', function() {
        location.hash = JSON.stringify({stack: [0], id: 1, ignore: [], hide: [], merged: false});
        //this.app.runRoute('get', '#' + JSON.stringify({stack: 1, id: 0}))
      });
  }).run();

  // Add the mouseleave handler to the bounding circle.
  d3.select("#container")
      .on("mouseleave", mouseleave)
      ;
 };
