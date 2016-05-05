
ginga_make_application = function (ws_url, debug_flag) {
        
    var ginga_app = {};
    
    ginga_app.ws_url = ws_url
    //ginga_app.socket = new WebSocket(ws_url);
    ginga_app.canvases = {}
    // set this to true to get javascript console debugging
    ginga_app.debug = debug_flag
    ginga_app.dialogs = {}
    ginga_app.tab_widgets = {}
    
    ginga_app.onmessage_handler = function(e) {
        try {
            message = JSON.parse(e.data);
            if (ginga_app.debug) console.log(message.operation);

            if (message.operation == "refresh_canvas") {
                if (message.id in ginga_app.canvases) {
                    ginga_app.canvases[message.id].redrawCanvas();
                };
            }
            else if (message.operation == "draw_canvas") {
                if (message.id in ginga_app.canvases) {
                    ginga_app.canvases[message.id].drawShape(message["shape"]);
                };
            }
            else if (message.operation == "dialog_action") {
                ginga_app.dialogs[message.id].fn(message.action);
	    }
            else if (message.operation == "set_tab") {
	        ginga_app.tab_widgets[message.id].fn(message.value);
            }
            else {
                elt = document.getElementById(message.id)
                if (elt == null) {
                    console.log("NULL document element--");
                    console.log(message.id);
                    return;
                }
                else if (message.operation == "update_label") {
                    // update widget value
                    elt.innerHTML = message.value;
                }
                else if (message.operation == "update_value") {
                    // update widget value
                    elt.value = message.value;
                }
                else if (message.operation == "update_index") {
                    // update widget value
                    elt.selectedIndex = message.value;
                }
                else if (message.operation == "update_html") {
                    // update widget content
                    elt.innerHTML = message.value;
                }
                else if (message.operation == "update_imgsrc") {
                    // update image content
                    elt.src = message.value;
                }
                else if (message.operation == "update_style") {
                    // update widget style
                    elt.setAttribute('style', message.value);
                }
                else if (message.operation == "disable") {
                    // update widget value
                    elt.disabled = message.value;
	        }
                else if (message.operation == "reload_page") {
                    // js 1.2-- do we need a check for this?
                    window.location.reload(true);
	        };
            };
        }
        catch (err) {
            console.log("Error performing operation:");
            console.log(err.message);
            console.log(message.operation);
            console.log(message.id);
            };
    };

    ginga_app.init_socket = function() {
        ginga_app.socket = new WebSocket(ginga_app.ws_url);
        ginga_app.socket.onmessage = ginga_app.onmessage_handler;
    }
  
    ginga_app.send_pkt = function (message) {
        var ws = ginga_app.socket;
        if (ws.readyState == WebSocket.CLOSED) {
            // try to reinitialize if the socket is closed
            console.log("web socket appears to be closed--trying to reopen...");
            ginga_app.init_socket();
            ws = ginga_app.socket;
            };
        ws.send(JSON.stringify(message));
        };
    
    ginga_app.widget_handler = function (id, value) {
        if (ginga_app.debug) console.log("callback for widget changed");
        var ws = ginga_app.socket;
        var message = {
            type: "activate",
            id: id,
            value: value,
        }
        ginga_app.send_pkt(message);
    }

    ginga_app.resize_window = function (e) {
        console.log("browser window is resized");
        e.preventDefault();

        for (var key in ginga_app.canvases) {
            ginga_app.canvases[key].resize_canvas(e)
        }
    }
    // document.body.addEventListener("resize", ginga_app.resize_window,
    //                                false);
    document.body.onresize = ginga_app.resize_window;

    ginga_app.init_socket();
  
    ginga_app.socket.onopen = function(e) {
        // initialize all our canvases
        for (var key in ginga_app.canvases) {
            ginga_app.canvases[key].initialize_canvas(e)
        }

        // report initial sizes
        ginga_app.resize_window(e)
    }

    return ginga_app;
}

ginga_initialize_canvas = function (canvas, id, app) {
    
    var pg_canvas = {};
    var is_touch_device = 'ontouchstart' in document.documentElement;

    pg_canvas.canvas_id = id
    pg_canvas.app = app
    app.canvases[id] = pg_canvas

    // request animation frame from browser
    pg_canvas.animFrame = window.requestAnimationFrame ||
        window.webkitRequestAnimationFrame ||
        window.mozRequestAnimationFrame ||
        window.oRequestAnimationFrame ||
        window.msRequestAnimationFrame;
    
    pg_canvas.send_pkt = app.send_pkt
    
    pg_canvas.context = canvas.getContext("2d");
    pg_canvas.hiddenCanvas = document.createElement("canvas");
    pg_canvas.hiddenCanvas.width = canvas.width;
    pg_canvas.hiddenCanvas.height = canvas.height;
    pg_canvas.hiddenContext = pg_canvas.hiddenCanvas.getContext("2d");
    
    pg_canvas.input_handler = function (e) {
        var message = {
            type: e.type || "",
            id: pg_canvas.canvas_id,
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
        pg_canvas.send_pkt(message);
    }
    
    pg_canvas.input_handler_suppress = function (e) {
        var message = {
            type: e.type || "",
            id: pg_canvas.canvas_id,
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
        pg_canvas.send_pkt(message);
    }
    
    pg_canvas.input_handler_gesture = function (e) {
        var message = {
            type: e.type || "",
            id: pg_canvas.canvas_id,
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
        pg_canvas.send_pkt(message);
    }
    
    pg_canvas.input_handler_focus = function (e) {
	canvas.focus()
	pg_canvas.input_handler(e)
    }

    pg_canvas.input_handler_drop = function (e) {
        e.preventDefault();
        var data = e.dataTransfer.getData("text/plain");
        //var data = e.dataTransfer.files;
        var message = {
            type: e.type || "",
            id: pg_canvas.canvas_id,
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
        pg_canvas.send_pkt(message);
    }
    
    pg_canvas.input_handler_suppress_only = function (e) {
        e.preventDefault();
    }
    
    //pg_canvas.resize_window = function resize_canvas(e) {
    pg_canvas.resize_canvas = function (e) {
        console.log("canvas " + pg_canvas.canvas_id + " resize cb");
        //e.preventDefault();
        canvas = document.getElementById(pg_canvas.canvas_id);
        console.log("current height is "+canvas.width.toFixed(0)+"x"+canvas.height.toFixed(0)+" pixels")

        // Set the canvas size to the pixel size reported for the
        // display area--important--we need to ensure no canvas scaling
        // so we can accurately maintain the peer's  pixel <--> data mapping
        width = canvas.clientWidth;
        height = canvas.clientHeight;
        console.log("client dimensions "+width.toFixed(0)+"x"+height.toFixed(0)+" pixels")

        // If an element is obscured it's size will be reported as 0.
        // In such a case we don't want to reset the peer's idea of the size
        // unnecessarily, so only report size changes > 0
        if ((width != 0) && (height != 0)) {
            canvas.width = width
            canvas.height = height
    
            // now resize hidden backing canvas
            pg_canvas.hiddenCanvas.width = width;
            pg_canvas.hiddenCanvas.height = height;
    
            // inform the other side about our new dimensions
            var message = { type: "resize",
                            id: pg_canvas.canvas_id,
                            width: width,
                            height: height
                          };
            pg_canvas.send_pkt(message);
            console.log("resized canvas");
        };
    }

    pg_canvas.redrawCanvas = function() {
        var ctx = pg_canvas.context;
        var hidCtx = pg_canvas.hiddenContext;
        var hidCvs = pg_canvas.hiddenCanvas;
        var animFrame = pg_canvas.animFrame;
    
        animFrame(function () {
            //ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(hidCvs, 0, 0);
            //console.log("Refresh canvas");
        });
    }
    
    pg_canvas.drawShape = function(shape) {
        var ctx = pg_canvas.hiddenContext;
        var operation = pg_canvas.shapeToFunc[shape["type"]];
        var animFrame = pg_canvas.animFrame;
    
        if (operation === undefined) {
            console.log("Could not find operation for shape " + shape["type"]);
        }
        animFrame(function () {
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
    
    pg_canvas.drawRect = function (ctx, rect) {
        if (rect.lineColor) {
            ctx.strokeStyle = rect.lineColor;
            ctx.strokeRect(rect.x, rect.y, rect.width, rect.height);
        }
        if (rect.fillColor) {
            ctx.fillStyle = rect.fillColor;
            ctx.fillRect(rect.x, rect.y, rect.width, rect.height);
        }
    }
    
    pg_canvas.clearRect = function (ctx, rect) {
            ctx.clearRect(rect.x, rect.y, rect.width, rect.height);
    }
    
    pg_canvas.drawCircle = function(ctx, circle) {
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
    
    pg_canvas.drawOval = function(ctx, oval) {
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
    
    pg_canvas.drawLine = function(ctx, line) {
        ctx.beginPath();
        ctx.moveTo(line.startX, line.startY);
        ctx.lineTo(line.endX, line.endY);
        ctx.strokeStyle = line.color || "#000";
        ctx.stroke();
    }
    
    pg_canvas.drawPolygon = function(ctx, polygon) {
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
    
    pg_canvas.drawImage = function(ctx, imgInfo) {
        var img = new Image();
        img.src = imgInfo.src;
        
        //var width = imgInfo.width || img.width;
        //var height = imgInfo.height || img.height;
    
        // Use an event listener, because otherwise if the draw happens
        // before the image is loaded you get nothing or an error in some
        // browsers (e.g. Mozilla)
        img.addEventListener("load", function () {
            //ctx.drawImage(img, imgInfo.x, imgInfo.y, width, height);
            ctx.drawImage(img, imgInfo.x, imgInfo.y);
            //console.log("drew image");
            })
    }
    
    pg_canvas.drawCompound = function(ctx, compound) {
        compound.shapes.forEach(function (shp) {
            pg_canvas.shapeToFunc[shp["type"]](ctx, shp);
        });
    }
    
    pg_canvas.shapeToFunc = {
        clear: pg_canvas.clearRect,
        rect: pg_canvas.drawRect,
        oval: pg_canvas.drawOval,
        circle: pg_canvas.drawCircle,
        image: pg_canvas.drawImage,
        line: pg_canvas.drawLine,
        polygon: pg_canvas.drawPolygon,
        compound: pg_canvas.drawCompound
    }
    
    var setup_canvas = function(e) {
        
        console.log("initializing canvas for events");

        // set up some event handlers for the canvas
        canvas.onmousedown = pg_canvas.input_handler;
        canvas.onmouseup   = pg_canvas.input_handler;
        canvas.onmousemove = pg_canvas.input_handler;
        canvas.onmouseout  = pg_canvas.input_handler;
        canvas.onmouseover = pg_canvas.input_handler_focus;
        canvas.onwheel = pg_canvas.input_handler_suppress;
        canvas.onmousewheel = pg_canvas.input_handler_suppress;
        canvas.onclick     = pg_canvas.input_handler;
        canvas.ondblclick  = pg_canvas.input_handler;
        canvas.ondrop      = pg_canvas.input_handler_drop;
        //canvas.onpaste   = pg_canvas.input_handler_drop;
        canvas.ondragover  = pg_canvas.input_handler_suppress_only;
        // disable right click context mentu
        canvas.oncontextmenu  = pg_canvas.input_handler_suppress_only;
        
        canvas.addEventListener("keydown", pg_canvas.input_handler, true);
        canvas.addEventListener("keyup", pg_canvas.input_handler, true);
        canvas.addEventListener("keypress", pg_canvas.input_handler, true);

        // enable touch events if this is a touch device
        if (is_touch_device) {
            pg_canvas.hammer = new Hammer(canvas, {})
            pg_canvas.hammer.get('pinch').set({ enable: true });
            pg_canvas.hammer.get('rotate').set({ enable: true });
            pg_canvas.hammer.get('pan').set({ direction: Hammer.DIRECTION_ALL });
            pg_canvas.hammer.on('pan', pg_canvas.input_handler_gesture)
            pg_canvas.hammer.on('panstart', pg_canvas.input_handler_gesture)
            pg_canvas.hammer.on('panend', pg_canvas.input_handler_gesture)
            pg_canvas.hammer.on('tap', pg_canvas.input_handler_gesture)
            pg_canvas.hammer.on('pinch', pg_canvas.input_handler_gesture)
            pg_canvas.hammer.on('pinchstart', pg_canvas.input_handler_gesture)
            pg_canvas.hammer.on('pinchend', pg_canvas.input_handler_gesture)
            pg_canvas.hammer.on('rotate', pg_canvas.input_handler_gesture)
            pg_canvas.hammer.on('rotatestart', pg_canvas.input_handler_gesture)
            pg_canvas.hammer.on('rotateend', pg_canvas.input_handler_gesture)
        }

        canvas.addEventListener("focus", pg_canvas.input_handler, true);
        //canvas.addEventListener("blur", pg_canvas.input_handler, true);
        canvas.addEventListener("focusout", pg_canvas.input_handler, true);

	canvas.style.cursor = 'crosshair';

        var message = { type: "setbounds",
                        id: pg_canvas.canvas_id,
                        width: canvas.width,
                        height: canvas.height
                        //width: canvas.clientWidth,
                        //height: canvas.clientHeight
                      };
        pg_canvas.send_pkt(message);
    }
    pg_canvas.initialize_canvas = setup_canvas
    
    return pg_canvas;
}

ginga_initialize_dialog = function (doc_elem, id, title, buttons, modal, app) {

    var pg_dialog = {};
    pg_dialog.dialog_id = id;
    pg_dialog.app = app;
    app.dialogs[id] = pg_dialog;

    pg_dialog.options = {autoOpen: false, modal: modal, title: title, buttons: buttons};

    pg_dialog.dialogObj = $("#"+id).dialog(pg_dialog.options);

    pg_dialog.fn = function(action) {
	pg_dialog.dialogObj.dialog(action);
    }

    return pg_dialog;
}

ginga_initialize_tab_widget = function (doc_elem, id, app) {

    var pg_tab_widget = {};
    pg_tab_widget.tab_widget_id = id;
    pg_tab_widget.app = app;
    app.tab_widgets[id] = pg_tab_widget;

    pg_tab_widget.options = {
	activate: function(event, ui) {ginga_app.widget_handler(id, ui.newTab.index());},
    };

    pg_tab_widget.tabObj = $("#"+id).tabs(pg_tab_widget.options);

    pg_tab_widget.fn = function(idx) {
	pg_tab_widget.tabObj.tabs("option", "active", idx);
    }

    return pg_tab_widget;
}
