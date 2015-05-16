
var reqAnimFrame = window.requestAnimationFrame ||
    window.webkitRequestAnimationFrame ||
    window.mozRequestAnimationFrame ||
    window.oRequestAnimationFrame ||
    window.msRequestAnimationFrame;

var pantograph = {};
pantograph.socket = new WebSocket(ws_url);

pantograph.canvas_id = canvas_id
pantograph.context = canvas.getContext("2d");
pantograph.hiddenCanvas = document.createElement("canvas");
pantograph.hiddenCanvas.width = canvas.width;
pantograph.hiddenCanvas.height = canvas.height;
pantograph.hiddenContext = pantograph.hiddenCanvas.getContext("2d");

pantograph.input_handler = function (e) {
    var ws = pantograph.socket;
    var message = {
	type: e.type || "",
	x: e.offsetX || e.clientX || 0,
	y: e.offsetY || e.clientY || 0,
	button: e.button || 0,
        delta: e.wheelDelta/120.0 || -e.deltaY/3.0 || 0,
	alt_key: e.altKey || false,
	ctrl_key: e.ctrlKey || false,
	meta_key: e.metaKey || false,
	shift_key: e.shiftKey || false,
	key_code: e.keyCode || e.which || 0
    }
    ws.send(JSON.stringify(message));
}

pantograph.input_handler_suppress = function (e) {
    var ws = pantograph.socket;
    var message = {
	type: e.type || "",
	x: e.offsetX || 0,
	y: e.offsetY || 0,
	button: e.button || 0,
        delta: e.wheelDelta/120.0 || -e.deltaY/3.0 || 0,
	alt_key: e.altKey || false,
	ctrl_key: e.ctrlKey || false,
	meta_key: e.metaKey || false,
	shift_key: e.shiftKey || false,
	key_code: e.keyCode || 0
    }
    e.preventDefault();
    ws.send(JSON.stringify(message));
}

pantograph.input_handler_gesture = function (e) {
    var ws = pantograph.socket;
    var message = {
	type: e.type || "",
	x: e.srcEvent.offsetX || 0,
	y: e.srcEvent.offsetY || 0,
	dx: e.deltaX || 0,
	dy: e.deltaY || 0,
	distance: e.distance || 0,
	theta: e.angle || 0,
        direction: e.direction || 0,
        vx: e.velocityX || 0,
        vy: e.velocityY || 0,
        scale: e.scale || 0,
        rotation: e.rotation || 0,
        isfirst: e.isFirst || false,
        isfinal: e.isFinal || false
    }
    e.preventDefault();
    ws.send(JSON.stringify(message));
}

pantograph.input_handler_drop = function (e) {
    var ws = pantograph.socket;
    e.preventDefault();
    var data = e.dataTransfer.getData("text/plain");
    //var data = e.dataTransfer.files;
    var message = {
	type: e.type || "",
	x: e.offsetX || 0,
	y: e.offsetY || 0,
	button: e.button || 0,
        delta: data,
	alt_key: e.altKey || false,
	ctrl_key: e.ctrlKey || false,
	meta_key: e.metaKey || false,
	shift_key: e.shiftKey || false,
	key_code: e.keyCode || 0
    }
    ws.send(JSON.stringify(message));
}

pantograph.input_handler_suppress_only = function (e) {
    e.preventDefault();
}

pantograph.resize_window = function resize_canvas(e) {
    console.log("canvas is resized");
    e.preventDefault();
    canvas = document.getElementById(pantograph.canvas_id);

    width = window.innerWidth;
    height = window.innerHeight;

    canvas.width = width;
    canvas.height = height;

    // now resize hidden backing canvas
    pantograph.hiddenCanvas.width = width;
    pantograph.hiddenCanvas.height = height;

    var ws = pantograph.socket;
    var message = {
	type: e.type || "",
	x: width || 0,
	y: height || 0,
	button: e.button || 0,
        delta: e.wheelDelta || 0,
	alt_key: e.altKey || false,
	ctrl_key: e.ctrlKey || false,
	meta_key: e.metaKey || false,
	shift_key: e.shiftKey || false,
	key_code: e.keyCode || 0
    }
    ws.send(JSON.stringify(message));
    console.log("resized canvas");
}

pantograph.redrawCanvas = function() {
    var ctx = pantograph.context;
    var hidCtx = pantograph.hiddenContext;
    var hidCvs = pantograph.hiddenCanvas;

    reqAnimFrame(function () {
	//ctx.clearRect(0, 0, canvas.width, canvas.height);
	ctx.drawImage(hidCvs, 0, 0);
        console.log("Refresh canvas");
    });
}

pantograph.drawShape = function(shape) {
    var ctx = pantograph.hiddenContext;
    var operation = pantograph.shapeToFunc[shape["type"]];
    if (operation === undefined) {
	console.log("Could not find operation for shape " + shape["type"]);
    }
    reqAnimFrame(function () {
	ctx.save();
	if (shape.rotate) {
	    ctx.translate(shape.rotate.x, shape.rotate.y);
	    ctx.rotate(shape.rotate.theta);
	    ctx.translate(-shape.rotate.x, -shape.rotate.y);
	}
	operation(ctx, shape);
	ctx.restore();
    });
}

pantograph.drawRect = function (ctx, rect) {
    if (rect.lineColor) {
	ctx.strokeStyle = rect.lineColor;
	ctx.strokeRect(rect.x, rect.y, rect.width, rect.height);
    }
    if (rect.fillColor) {
	ctx.fillStyle = rect.fillColor;
	ctx.fillRect(rect.x, rect.y, rect.width, rect.height);
    }
}

pantograph.clearRect = function (ctx, rect) {
	ctx.clearRect(rect.x, rect.y, rect.width, rect.height);
}

pantograph.drawCircle = function(ctx, circle) {
    ctx.beginPath();
    ctx.arc(circle.x, circle.y, circle.radius, 0, 2 * Math.PI, true);
    if (circle.lineColor) {
	ctx.strokeStyle = circle.lineColor;
	ctx.stroke();
    }
    if (circle.fillColor) {
	ctx.fillStyle = circle.fillColor;
	ctx.fill();
    }
}

pantograph.drawOval = function(ctx, oval) {
    var x = oval.x + oval.width / 2;
    var y = oval.y + oval.height / 2;
    
    ctx.save();
    ctx.translate(x, y);
    
    ctx.scale(oval.width, oval.height);
    
    ctx.beginPath();
    ctx.arc(0, 0, 0.5, 0, 2 * Math.PI, true);
    
    ctx.restore();
    
    if (oval.lineColor) {
	ctx.strokeStyle = oval.lineColor;
	ctx.stroke();
    }
    
    if (oval.fillColor) {
	ctx.fillStyle = oval.fillColor;
	ctx.fill();
    }
}

pantograph.drawLine = function(ctx, line) {
    ctx.beginPath();
    ctx.moveTo(line.startX, line.startY);
    ctx.lineTo(line.endX, line.endY);
    ctx.strokeStyle = line.color || "#000";
    ctx.stroke();
}

pantograph.drawPolygon = function(ctx, polygon) {
    var startX = polygon.points[0][0];
    var startY = polygon.points[0][1];
    
    ctx.beginPath();
    ctx.moveTo(startX, startY);
    
    polygon.points.slice(1).forEach(function (pt) {
	ctx.lineTo(pt[0], pt[1]);
    });
    
    ctx.lineTo(startX, startY);
    
    if (polygon.lineColor) {
	ctx.strokeStyle = polygon.lineColor;
	ctx.stroke();
    }
    
    if (polygon.fillColor) {
	ctx.fillStyle = polygon.fillColor;
	ctx.fill();
    }
}

pantograph.drawImage = function(ctx, imgInfo) {
    var img = new Image();
    img.src = imgInfo.src;
    
    //var width = imgInfo.width || img.width;
    //var height = imgInfo.height || img.height;

    // Use an event listener, because otherwise if the draw happens
    // before the image is loaded you get nothing or an error in some
    // browsers ("Mozilla", *cough*)
    img.addEventListener("load", function () {
        //ctx.drawImage(img, imgInfo.x, imgInfo.y, width, height);
        ctx.drawImage(img, imgInfo.x, imgInfo.y);
        console.log("drew image");
        })
}

pantograph.drawCompound = function(ctx, compound) {
    compound.shapes.forEach(function (shp) {
	pantograph.shapeToFunc[shp["type"]](ctx, shp);
    });
}

pantograph.shapeToFunc = {
    clear: pantograph.clearRect,
    rect: pantograph.drawRect,
    oval: pantograph.drawOval,
    circle: pantograph.drawCircle,
    image: pantograph.drawImage,
    line: pantograph.drawLine,
    polygon: pantograph.drawPolygon,
    compound: pantograph.drawCompound
}

pantograph.socket.onopen = function(e) {
    canvas.onmousedown = pantograph.input_handler;
    canvas.onmouseup   = pantograph.input_handler;
    canvas.onmousemove = pantograph.input_handler;
    canvas.onmouseout  = pantograph.input_handler;
    canvas.onmouseover = pantograph.input_handler;
    canvas.onwheel = pantograph.input_handler_suppress;
    canvas.onclick     = pantograph.input_handler;
    canvas.ondblclick  = pantograph.input_handler;
    canvas.ondrop      = pantograph.input_handler_drop;
    //canvas.onpaste   = pantograph.input_handler_drop;
    canvas.ondragover  = pantograph.input_handler_suppress_only;
    // disable right click context mentu
    canvas.oncontextmenu  = pantograph.input_handler_suppress_only;
    
    document.body.onkeydown  = pantograph.input_handler;
    document.body.onkeyup    = pantograph.input_handler;
    document.body.onkeypress = pantograph.input_handler;
    document.body.onresize = pantograph.resize_window;
    document.body.onfocus = pantograph.input_handler;
    document.body.onblur = pantograph.input_handler;
    
    pantograph.socket.send(JSON.stringify({
	type: "setbounds", width: canvas.width, height: canvas.height
    }));
}

pantograph.socket.onmessage = function(e) {
    message = JSON.parse(e.data);
    if (message.operation == "refresh")
	pantograph.redrawCanvas();
    else if (message.operation == "draw")
	pantograph.drawShape(message["shape"]);
}
