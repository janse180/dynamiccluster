var frequency = 0;
var timer ;
var refresh_count=0;
var graph_list=[];
var metrics_url;
function initWNView(){
	  $('#wntab').addClass('active');
	  $('#jtab').removeClass('active');
	  $('#rtab').removeClass('active');
	  $('#gtab').removeClass('active');
	  $('#stab').removeClass('active');
	  $("#main").html('<div class="panel panel-default"><div class="panel-heading">Worker Nodes</div><div class="table-responsive"><table class="table table-striped table-condensed"><thead>'+
			  '<tr><th>Hostname</th><th>Type</th><th>Instance Name</th><th>VCPUS</th><th>State</th><th>IP</th><th>State In Cloud</th><th>In current state for</th>'+
			  '<th>Resource</th><th>Jobs</th></tr></thead><tbody id="wntable"></tbody></table></div></div>');
	  $.getJSON( "/workernode", function( data ) {
		  var items = [];
		  var nodes = [];
		  //alert(data);
		  $.each( data, function( key, val ) {
			  //alert(val.id);
			  //console.log(val);
			  resource="";
			  ip="";
			  cloud_state="";
			  instance_name="";
			  if (val.instance) {
				  resource=val.instance.cloud_resource;
				  instance_name=val.instance.instance_name;
				  if (val.instance.ip) ip=val.instance.ip;
				  cloud_state=convertCloudState(val.instance.state);
			  }
			  jobs="";
			  if (val.jobs) jobs=val.jobs;
			  $('#wntable').append('<tr><th><a href=\'javascript:showWorkerNode("'+val.hostname+'")\'>'+val.hostname+'</a></th><td>'+val.type+'</td><td>'+instance_name+'</td><td>'+val.num_proc+'</td><td>'+
					  convertWNState(val.state)+'</td><td>'+ip+'</td><td>'+cloud_state+'</td><td>'+convertTimeInCurrentState(val.time_in_current_state)+
					  '</td><td>'+resource+'</td><td>'+jobs+'</td></tr>'); 
		  });
		});
}

function convertTimeInCurrentState(t) {
	if (t/60>0) {
		return parseInt(t/60)+"m"+parseInt(t%60)+"s";
	}
	return parseInt(t)+"s";
}

function showWorkerNode(hostname) {
	$.getJSON( "/workernode/"+hostname, function( data ) {
		console.log(data);
		$('#modalLabel').html(hostname);
		htmlstr='<table style="width: auto;" class="table table-striped">'+
				'<tr><th>Hostname</th><td>'+data.hostname+'</td></tr>'+
				'<tr><th>Type</th><td>'+data.type+'</td></tr>'+
				'<tr><th>VCPUS</th><td>'+data.num_proc+'</td></tr>'+
				'<tr><th>State</th><td>'+convertWNState(data.state)+'</td></tr>'+
				'<tr><th>In current state for</th><td>'+convertTimeInCurrentState(data.time_in_current_state)+'</td></tr>';
		if (data.jobs) {
			htmlstr+='<tr><th>Jobs</th><td>'+data.jobs+'</td></tr>';
		}
		if (data.instance) {
			htmlstr+='<tr><th>Instance Name</th><td>'+data.instance.instance_name+'</td></tr>'+
					'<tr><th>UUID</th><td>'+data.instance.uuid+'</td></tr>'+
					'<tr><th>Cloud Resource</th><td>'+data.instance.cloud_resource+'</td></tr>'+
					'<tr><th>IP</th><td>'+data.instance.ip+'</td></tr>'+
					'<tr><th>DNS Name</th><td>'+data.instance.dns_name+'</td></tr>'+
					'<tr><th>State</th><td>'+convertCloudState(data.instance.state)+'</td></tr>'+
					'<tr><th>Flavor</th><td>'+data.instance.flavor+'</td></tr>'+
					'<tr><th>VCPU Number</th><td>'+data.instance.vcpu_number+'</td></tr>'+
					'<tr><th>Availability Zone</th><td>'+data.instance.availability_zone+'</td></tr>'+
					'<tr><th>Key Name</th><td>'+data.instance.key_name+'</td></tr>'+
					'<tr><th>Security Groups</th><td>'+data.instance.security_groups+'</td></tr>'+
					'<tr><th>Creation Time</th><td>'+moment.unix(data.instance.creation_time).format("YYYY-M-D h:mm:ss")+'</td></tr>'+
					'<tr><th>Last Update Time</th><td>'+moment.unix(data.instance.last_update_time).format("YYYY-M-D h:mm:ss")+'</td></tr>'+
					'<tr><th>In Task</th><td>'+data.instance.tasked+'</td></tr>'+
					'<tr><th>Last Task Result</th><td>'+data.instance.last_task_result+'</td></tr>';
		}		
		htmlstr+='<tr><th>Extra Attributes</th><td>&nbsp;</td></tr>';
		if (data.extra_attributes) {
			$.each(data.extra_attributes, function( key, val ) {
				htmlstr+='<tr><th>'+key+'</th><td>'+val.replace(/,/g,", ")+'</td></tr>';
			});
		}
		htmlstr+='</table>';
		$('#modalMain').html(htmlstr);
		$('#infoDialog').modal('show');
	});
}

function convertCloudState(s){ //Inexistent, Pending, Starting, Active, Ready, Deleting, Error, Unknown = range(8)
	if (s==0) return "Inexistent";
	if (s==1) return "Pending";
	if (s==2) return "Starting";
	if (s==3) return "Active";
	if (s==4) return "Ready";
	if (s==5) return "Deleting";
	if (s==6) return "Error";
	return "Unknown";
}
function convertWNState(s) { //Inexistent, Starting, Idle, Busy, Error, Deleting, Holding, Held
	if (s==1) return "Starting";
	if (s==2) return "Idle";
	if (s==3) return "Busy";
	if (s==4) return "Error";
	if (s==5) return "Deleting";
	if (s==6) return "Holding";
	if (s==7) return "Held";
	return "Inexistent";
}

function initJobView(){
	  $('#wntab').removeClass('active');
	  $('#jtab').addClass('active');
	  $('#rtab').removeClass('active');
	  $('#gtab').removeClass('active');
	  $('#stab').removeClass('active');
	  $("#main").html('<div class="panel panel-default"><div class="panel-heading">Jobs</div><div class="table-responsive"><table class="table table-striped table-condensed"><thead><tr><th>Job Id</th><th>Name</th><th>State</th><th>Priority</th><th>Owner</th><th>Queue</th><th>Account</th><th>Property</th><th>Req. Walltime</th><th>Req. Mem</th><th>Req. Proc</th><th>Creation Time</th></tr></thead><tbody id="jtable"></tbody></table></div></div>');
	  $.getJSON( "/job", function( data ) {
		  var items = [];
		  var nodes = [];
		  //alert(data);
		  $.each( data, function( key, val ) {
			  //alert(val.id);
			  //console.log(val);
			  queue="&nbsp;";
			  if (val.queue) queue=val.queue;
			  account="&nbsp;";
			  if (val.account) account=val.account;
			  property="&nbsp;";
			  if (val.property) property=val.property;
			  requested_walltime="&nbsp;";
			  if (val.requested_walltime) requested_walltime=val.requested_walltime;
			  requested_mem="&nbsp;";
			  if (val.requested_mem) requested_mem=val.requested_mem;
			  $('#jtable').append('<tr><th><a href=\'javascript:showJob("'+val.jobid+'")\'>'+val.jobid+'</a></th><td>'+val.name+'</td><td>'+convertJobState(val.state)+'</td><td>'+val.priority+'</td><td>'+val.owner+'</td><td>'+queue+'</td><td>'+account+'</td><td>'+property+'</td><td>'+requested_walltime+'</td><td>'+requested_mem+'</td><td>'+convertProc(val)+'</td><td>'+moment.unix(val.creation_time).format("YYYY-M-D h:mm:ss")+'</td></tr>'); 
		  });
		});
}

function convertJobState(s) {
	if (s==0) return "Queued";
	if (s==1) return "Running";
	return "Other";
}

function convertProc(p) {
	return p.requested_cores+"cores("+p.cores_per_node+"pn)";
}

function showJob(jobid) {
	$.getJSON( "/job/"+jobid, function( data ) {
		console.log(data);
		$('#modalLabel').html(jobid);
		htmlstr='<table style="width: auto;" class="table table-striped">'+
				'<tr><th>Job ID</th><td>'+data.jobid+'</td></tr>'+
				'<tr><th>Name</th><td>'+data.name+'</td></tr>'+
				'<tr><th>Priority</th><td>'+data.priority+'</td></tr>'+
				'<tr><th>State</th><td>'+convertJobState(data.state)+'</td></tr>'+
				'<tr><th>Owner</th><td>'+data.owner+'</td></tr>';
		if (data.queue) {
			htmlstr+='<tr><th>Queue</th><td>'+data.queue+'</td></tr>';
		}
		if (data.account) {
			htmlstr+='<tr><th>Account</th><td>'+data.account+'</td></tr>';
		}
		if (data.property) {
			htmlstr+='<tr><th>Property</th><td>'+data.property+'</td></tr>';
		}
		if (data.requested_walltime) {
			htmlstr+='<tr><th>Requested Walltime</th><td>'+data.requested_walltime+'</td></tr>';
		}
		if (data.requested_mem) {
			htmlstr+='<tr><th>Requested Memory</th><td>'+data.requested_mem+'</td></tr>';
		}
		htmlstr+='<tr><th>Requested Processors</th><td>'+convertProc(data)+'</td></tr>';
		htmlstr+='<tr><th>Creation Time</th><td>'+moment.unix(data.creation_time).format("YYYY-M-D h:mm:ss")+'</td></tr>';
		htmlstr+='<tr><th>Extra Attributes</th><td>&nbsp;</td></tr>';
		if (data.extra_attributes) {
			$.each(data.extra_attributes, function( key, val ) {
				htmlstr+='<tr><th>'+key+'</th><td>'+val.replace(/,/g,", ")+'</td></tr>';
			});
		}
		htmlstr+='</table>';
		$('#modalMain').html(htmlstr);
		$('#infoDialog').modal('show');
	});
}

function initResourceView() {
	  $('#wntab').removeClass('active');
	  $('#jtab').removeClass('active');
	  $('#gtab').removeClass('active');
	  $('#stab').removeClass('active');
	  $('#rtab').addClass('active');
	  //$("#main").html('<div class="panel panel-default"><div class="panel-heading">Resources</div><div class="table-responsive"><table class="table table-striped table-condensed"><thead><tr><th>Job Id</th><th>Name</th><th>State</th><th>Priority</th><th>Owner</th><th>Queue</th><th>Account String</th><th>Req. Walltime</th><th>Req. Mem</th><th>Req. Proc</th><th>Creation Time</th></tr></thead><tbody id="rtable"></tbody></table></div></div>');
	  $.getJSON( "/resource", function( data ) {
		  var items = [];
		  var nodes = [];
		  //alert(data);
		  htmlstr='<div class="panel-group" id="accordion">';
		  $.each( data, function( key, val ) {
			  //alert(val.id);
			  console.log(val);
			  htmlstr+='<div class="panel panel-default" id="panel'+val.name+'"><div class="panel-heading"><h4 class="panel-title"><a data-toggle="collapse" data-target="#collapse'+val.name+'" href="#collapse'+val.name+'">'+val.name+'</a></h4></div><div id="collapse'+val.name+'" class="panel-collapse collapse in"><div class="panel-body">';
			  htmlstr+='<div style="padding: 3px; float: left; width: 75%; text-align: left;"><h5><span class="label label-primary">Type</span>'+val.type+' <span class="label label-primary">Priority</span>'+val.priority+' <span class="label label-primary">Min</span> '+val.min_num+' <span class="label label-primary">Current</span> '+val.current_num+' <span class="label label-primary">Max</span> '+val.max_num+'&nbsp;&nbsp;';
			  if (val.reservation_queue) htmlstr+='<span class="label label-success">Reservation</span><span class="label label-info">Queue</span>&nbsp;'+val.reservation_queue+'&nbsp;&nbsp;';
			  if (val.reservation_property) htmlstr+='<span class="label label-success">Reservation</span><span class="label label-info">Property</span>&nbsp;'+val.reservation_property+'&nbsp;&nbsp;';
			  if (val.reservation_account) htmlstr+='<span class="label label-success">Reservation</span><span class="label label-info">Account</span>&nbsp;'+val.reservation_account+'&nbsp;&nbsp;';
			  htmlstr+='<button type="button" class="btn btn-success btn-sm" id="addbutton'+val.name+'" data-toggle="modal" data-target="#addResDialog" data-whatever="'+val.name+'">Add</button>&nbsp;';
			  htmlstr+='<button type="button" class="btn btn-danger btn-sm" id="removebutton'+val.name+'" data-toggle="modal" data-target="#modifyResDialog" data-action="remove" data-whatever="'+val.name+'">Remove</button>&nbsp;';
			  htmlstr+='<button type="button" class="btn btn-warning btn-sm" id="holdbutton'+val.name+'" data-toggle="modal" data-target="#modifyResDialog" data-action="hold" data-whatever="'+val.name+'">Hold</button>&nbsp;';
			  htmlstr+='<button type="button" class="btn btn-warning btn-sm" id="unholdbutton'+val.name+'" data-toggle="modal" data-target="#modifyResDialog" data-action="unhold" data-whatever="'+val.name+'">Unhold</button>&nbsp;';
			  htmlstr+='<button type="button" class="btn btn-warning btn-sm" id="vacatebutton'+val.name+'" data-toggle="modal" data-target="#modifyResDialog" data-action="vacate" data-whatever="'+val.name+'">Vacate</button></h5></div>';
			  percentage=parseInt(val.current_num*100/val.max_num);
			  htmlstr+='<div class="progress"><div class="progress-bar" role="progressbar" aria-valuenow="'+percentage+'" aria-valuemin="0" aria-valuemax="100" style="width: '+percentage+'%;">'+percentage+'%</div></div></div>';
			  htmlstr+='<table class="table table-striped table-condensed" id="table'+val.name+'"><thead><tr><th>&nbsp;</th><th>Hostname</th><th>Instance Name</th><th>VCPUS</th><th>State</th><th>IP</th><th>State In Cloud</th><th>Jobs</th></tr></thead><tbody>';
			  $.each(val.worker_nodes, function(key1, val1){
				  console.log(val1);
				  jobs='';
				  ip='';
				  if (val1.jobs) jobs=val1.jobs;
				  if (val1.instance.ip) ip=val1.instance.ip;
				  htmlstr+='<tr><th><input class="checkbox" type="checkbox" value="'+val1.hostname+'"></th><th><a href=\'javascript:showWorkerNode("'+val1.hostname+'")\'>'+val1.hostname+'</a></th><td>'+val1.instance.instance_name+'</td><td>'+val1.num_proc+'</td><td>'+convertWNState(val1.state)+'</td><td>'+ip+'</td><td>'+convertCloudState(val1.instance.state)+'</td><td>'+jobs+'</td></tr>';
			  });
			  htmlstr+='</tbody></table></div></div>';
		  });
		  htmlstr+='</div>';
		  //console.log(htmlstr);
		  $("#main").html(htmlstr);
		});
}

function addAlert(type, message) {
    $('#alertMessages').append(
            '<div class="alert alert-'+type+' alert-dismissible">' +
                '<button type="button" class="close" data-dismiss="alert">' +
                '&times;</button>' + message + '</div>');
}

function addResource(res_name, num){
	//console.log(res_name+" "+n);
	$.ajax({
        type: "PUT",
        url: "/resource/"+res_name+"?num="+num,
        success: function(response) {
	    //console.log(response);
		    if (response["success"]==true){
		    	//$("#successalert").show();
		    	addAlert("success", "Successfully sent a request to launch "+num+" worker node(s) in "+res_name+".");
		    	initResourceView();
		    }else
		    	addAlert("danger", "Server error");
        },
	    error: function(jqXHR, textStatus, errorThrown) {
	        console.log(jqXHR.status);
	        addAlert("danger", jqXHR.responseText);
//	        if (jqXHR.status==404) {
//	        	addAlert("danger", "Resource "+res_name+" not found.");
//	        } else if (jqXHR.status==400) {
//	        	addAlert("danger", "You have requested "+num+" worker node(s) in "+res_name+" but it has exceeded the resource limit.");
//		    	//$("#failalert").show();
//	        } else if (jqXHR.status==500) {
//	        	addAlert("danger", "Server error");
//	        }
	        initResourceView();
	        //console.log(textStatus);
	        //console.log(errorThrown);
	    }
	});
	
}

function modifyResource(wn, action){
	console.log(action+" "+wn);
	req_type="PUT";
	if (action=="remove") req_type="DELETE";
	req_url="/workernode/"+wn;
	if (action!="remove") req_url+="/"+action;
	$.ajax({
        type: req_type,
        url: req_url,
        success: function(response) {
		    console.log(response);
		    if (response["success"]==true){
		    	addAlert("success", "Successfully sent a request to "+action+" worker node "+wn+".");
		    }else
		    	addAlert("danger", "Server error");
	    	refresh_count-=1;
	    	if (refresh_count<=0) {
	    		console.log("refresh resource view");
	    		initResourceView();
	    	}
	    },
	    error: function(jqXHR, textStatus, errorThrown) {
	        //console.log(jqXHR);
	        //console.log(jqXHR.status);
	        //console.log(textStatus);
	        //console.log(errorThrown);
	        addAlert("danger", jqXHR.responseText);
	    },
	    always: function(jqXHR) {
	    	refresh_count-=1;
	    	if (refresh_count<=0) {
	    		console.log("refresh resource view");
	    		initResourceView();
	    	}
	    }
	});
	
}


$('#addResDialog').on('show.bs.modal', function (event) {
	  var button = $(event.relatedTarget); // Button that triggered the modal
	  var res_name = button.data('whatever'); // Extract info from data-* attributes
	  // If necessary, you could initiate an AJAX request here (and then do the updating in a callback).
	  // Update the modal's content. We'll use jQuery here, but you could use a data binding library or other methods instead.
	  var modal = $(this);
	  modal.find('.modal-title').text('Launch new instances for resource ' + res_name);
	  $('#resname').val(res_name);
	  modal.find('.modal-body input:text').css({ "border":""});
	  modal.find('.modal-body input:text').tooltip('hide');
});
$('#addResDialog').find('.modal-body button').click(function() {
	inputbox=$('#addResDialog').find('.modal-body input:text');
    //console.log(inputbox);
    n=inputbox.val();
    //console.log($.isNumeric(n));
    if ($.isNumeric(n)) {
	    $('#addResDialog').modal('hide');
	    addResource($('#resname').val(), n);
    }else{
    	inputbox.css({ "border": '#FF0000 1px solid'});
    	inputbox.tooltip('show');
    }
});
$('#modifyResDialog').on('show.bs.modal', function (event) {
	var selected = [];
	var button = $(event.relatedTarget); // Button that triggered the modal
	var res_name = button.data('whatever');
	var action = button.data('action');
	console.log(action);
	$('#table'+res_name+' input:checked').each(function() {
	    selected.push($(this).val());
	});
	if (selected.length==0) {
		$("#modifyResModalMain").html("Please select worker nodes.");
		$('#modifyResDialog').find('.modal-footer .btn-primary').prop('disabled', true);
	} else {
		$("#modifyResModalLabel").html("Selected Worker Nodes:");
		htmlStr="Do you really want to "+action+" the following worker nodes?<ul id='nodesList'>";
		$.each( selected, function( key, val ) {
			htmlStr+='<li>'+val+'</li>';
		});
		htmlStr+="</ul>";
		refresh_count=selected.length;
		$("#modifyResModalMain").html(htmlStr);
		$('#modifyResDialog').find('.modal-footer .btn-primary').prop('disabled', false);
		$('#modifyResDialog').find('.modal-footer input:hidden').val(action);
	}
    //console.log($.isNumeric(n));
});

$('#modifyResDialog').find('.modal-footer .btn-primary').click(function() {
	var action=$('#modifyResDialog').find('.modal-footer input:hidden').val();
	console.log("button action:"+action);
	$('#nodesList').each(function() {
		$(this).find('li').each(function(){
			modifyResource($(this).text(), action);
			//removeResource($(this).text());
		});
	});
	$('#modifyResDialog').modal('hide');
});

function initGraphView() {
	  $('#wntab').removeClass('active');
	  $('#jtab').removeClass('active');
	  $('#gtab').addClass('active');
	  $('#stab').removeClass('active');
	  $('#rtab').removeClass('active');
	  console.log("graph view:"+graph_view);
	  if (graph_view){
		  prefix=graphite_prefix;
		  hostname=graphite_hostname;
		  if (hostname=="localhost") hostname=window.location.hostname;
		  $.fn.graphite.defaults.url = "http://"+hostname+":8080/render";
		  metrics_url="http://"+hostname+":8080/metrics/find";
		  htmlStr='<div class="row"><div class="row"><div class="col-md-8">&nbsp;</div>'+
				  '<div class="col-md-4">From <input type=text id=from value="-3h"> To <input type=text id=to value="Now"> <button type="button" class="btn btn-info" id="go" rel="popover">Go</button></div></div>'+
				  '<div class="row"><div class="col-md-2"><div class="sidebar-nav"><div class="navbar navbar-default" role="navigation">'+
				  '<div class="navbar-collapse collapse sidebar-navbar-collapse"><ul class="nav navbar-nav" id="graphmenu">'+
		          '<li id="dtgraphtab" class="active"><a href="javascript:showDTGraph()">Dynamic Cluster</a></li>';
		  if (wn_prefix!='') 
			  htmlStr+='<li id="wngraphtab"><a href="javascript:showWNOverview()">Worker Nodes</a></li><li class="divider"></li>';
		  htmlStr+='</ul></div></div></div></div><div class="col-md-10" id="graphmain">'+
				  '</div></div>';
		  $("#main").html(htmlStr);
		  showDTGraph();
		  if (wn_prefix!='') {
			  $.getJSON( metrics_url+"?query="+wn_prefix+"*", function( data ) {
				  var items = [];
				  //alert(data);
				  $.each( data, function( key, val ) {
					  //alert(val.id);
					  items.push(val.id);
				  });
				 
				  items.forEach(function(id){
					  //alert( p);
					  $("#graphmenu").append("<li id='"+id+"tab'><a href='javascript:showWNGraph(\""+id+"\")'>&nbsp;&nbsp;"+id+"</a></li>");
				  });
				});
		  }
		  $('#go').click(function(){
				//alert($("#from").val()+$("#to").val());
				var opts={from: $("#from").val()};
				if ($("#to").val().toLowerCase()!="now") opts['until']=$("#to").val();
				//alert(opts.from+" "+opts.until);
				for (var i=0;i<graph_list.length;i++){
					//alert(graphs[i]);
					$.fn.graphite.update($(graph_list[i]), opts);
				}
//				$.fn.graphite.update($("#nodeview"), opts);
//				$.fn.graphite.update($("#coreview"), opts);
//				$.fn.graphite.update($("#resnodeview"), opts);
//				$.fn.graphite.update($("#rescoreview"), opts);
			});
	  }else{
		  $("#main").html('<div class="well well-lg">You need to define graphite plugin to enable graph view.</div>');
	  }
}

function showDTGraph() {
	$('#graphmenu').find('li').each(function(){
		$(this).removeClass('active');
	});
	$('#dtgraphtab').addClass('active');
	$("#graphmain").html('<div class="row"><div class="col-md-6"><img id="nodeview" class="center-block"/></div><div class="col-md-6"><img id="coreview" class="center-block"/></div></div>'+
			  '<div class="row"><div class="col-md-6"><img id="resnodeview" class="center-block"/></div><div class="col-md-6"><img id="rescoreview" class="center-block"/></div></div>');
	  $("#nodeview").graphite({
		    from: $("#from").val(),
		    to: $("#to").val(),
		    colorList: "black,grey,red,brown,green,darkgreen,yellow",
		    target: [
		        "alias("+prefix+".nodes.total,'Total')",
		        "alias(stacked("+prefix+".nodes.deleting),'Deleting')",
		        "alias(stacked("+prefix+".nodes.error),'Error')",
		        "alias(stacked("+prefix+".nodes.vacating),'Vacating')",
		        "alias(stacked("+prefix+".nodes.busy),'Busy')",
		        "alias(stacked("+prefix+".nodes.idle),'Idle')",
		        "alias(stacked("+prefix+".nodes.starting),'Starting')"
		    ],
		    lineWidth: "2",
		    width: "600",
		    height: "400",
		    title: "Number of Worker Nodes"
	  });
	  $("#coreview").graphite({
		    from: $("#from").val(),
		    to: $("#to").val(),
		    colorList: "black,grey,red,brown,green,darkgreen,yellow",
		    target: [
		        "alias("+prefix+".cores.total,'Total')",
		        "alias(stacked("+prefix+".cores.deleting),'Deleting')",
		        "alias(stacked("+prefix+".cores.error),'Error')",
		        "alias(stacked("+prefix+".cores.vacating),'Vacating')",
		        "alias(stacked("+prefix+".cores.busy),'Busy')",
		        "alias(stacked("+prefix+".cores.idle),'Idle')",
		        "alias(stacked("+prefix+".cores.starting),'Starting')"
		    ],
		    lineWidth: "2",
		    width: "600",
		    height: "400",
		    title: "Number of Cores"
	  });
	  $("#resnodeview").graphite({
		    from: $("#from").val(),
		    colorList: "red,orange,green,blue,yellow,brown,purple",
		    target: [
		        "aliasByNode(stacked("+prefix+".resource.*.nodes),3)"
		    ],
		    yMin: "0",
		    lineWidth: "2",
		    width: "600",
		    height: "400",
		    title: "Number of Worker Nodes by Resource"
	  });
	  $("#rescoreview").graphite({
		    from: $("#from").val(),
		    colorList: "red,orange,green,blue,yellow,brown,purple",
		    target: [
		        "aliasByNode(stacked("+prefix+".resource.*.cores),3)"
		    ],
		    yMin: "0",
		    lineWidth: "2",
		    width: "600",
		    height: "400",
		    title: "Number of Cores by Resource"
	  });
	  graph_list=["#nodeview","#coreview","#resnodeview","#rescoreview"];
}

function showWNOverview() {
	$('#graphmenu').find('li').each(function(){
		$(this).removeClass('active');
	});
	$('#wngraphtab').addClass('active');
	$("#graphmain").html('<div class="row"><div class="col-md-6"><img id="load1view" class="center-block"/></div>'+
			'<div class="col-md-6"><img id="load15view" class="center-block"/></div></div>');
	  $("#load1view").graphite({
		  from: $("#from").val(),
		  to: $("#to").val(),
	    target: ["aliasByNode(stacked("+wn_prefix+"*.load.1min),0)"],
	    hideLegend: "false",
	    lineWidth: "1",
	    width: "600",
	    height: "400",
	    title: "Worker Nodes Overview"
	  });
}

function showWNGraph(id) {
	$('#graphmenu').find('li').each(function(){
		$(this).removeClass('active');
	});
	$('#'+id+'tab').addClass('active');
	$("#graphmain").html('<div class="row"><div class="col-md-4"><img id="load1view" class="center-block"/></div>'+
			'<div class="col-md-4"><img id="load5view" class="center-block"/></div>'+
			'<div class="col-md-4"><img id="load15view" class="center-block"/></div></div>');
	$("#load1view").graphite({
	  from: $("#from").val(),
	  to: $("#to").val(),
	  target: [
             "alias("+id+".load.1min,'"+id+" Load 1m')"
	  ],
	  lineWidth: "1",
	  width: "400",
	  height: "300",
	});
	$("#load5view").graphite({
		  from: $("#from").val(),
		  to: $("#to").val(),
		  target: [
	             "alias("+id+".load.5min,'"+id+" Load 5m')"
		  ],
		  lineWidth: "1",
		  width: "400",
		  height: "300",
		});
	$("#load15view").graphite({
		  from: $("#from").val(),
		  to: $("#to").val(),
		  target: [
	             "alias("+id+".load.15min,'"+id+" Load 15m')"
		  ],
		  lineWidth: "1",
		  width: "400",
		  height: "300",
		});
	  graph_list=["#load1view","#load5view","#load15view"];
}

function initSettingView() {
	  $('#wntab').removeClass('active');
	  $('#jtab').removeClass('active');
	  $('#gtab').removeClass('active');
	  $('#stab').addClass('active');
	  $('#rtab').removeClass('active');
	  $("#main").html('<div id="statusdiv" class="panel panel-default"></div>'+
			  '<div id="configdiv" class="panel panel-default"></div>');
	  showServerStatus();
	  $.getJSON( "/server/config", function( data ) {
		  console.log(data);
		  htmlStr='<div class="panel-heading"><h3 class="panel-title">Server Config</h3></div><table class="table table-condensed"><tr><th colspan="2">General</th></tr>';
		  $.each( data['dynamic-cluster'], function( key, val ) {
			  if (typeof val === 'object') {
				  htmlStr+='<tr><td class="info">'+key+'</td><td>'+JSON.stringify(val)+'</td></tr>';
			  }else
				  htmlStr+='<tr><td class="info">'+key+'</td><td>'+val+'</td></tr>';
		  });
		  htmlStr+='<tr><th colspan="2">Cluster: '+data['cluster']['type']+'</th></tr>';
		  $.each( data['cluster']['config'], function( key, val ) {
			  if (typeof val === 'object') {
				  htmlStr+='<tr><td class="info">'+key+'</td><td>'+JSON.stringify(val)+'</td></tr>';
			  }else
				  htmlStr+='<tr><td class="info">'+key+'</td><td>'+val+'</td></tr>';
		  });
		  $.each( data['cloud'], function( key, val ) {
			  htmlStr+='<tr><th colspan="2">Cloud Resource: '+key+'</th></tr>';
			  $.each( val, function( key1, val1 ) {
				  if (typeof val1 === 'object') {
					  htmlStr+='<tr><td class="info">'+key1+'</td><td>'+dictToTable(val1)+'</td></tr>';
				  }else
					  htmlStr+='<tr><td class="info">'+key1+'</td><td>'+val1+'</td></tr>';
			  });
		  });
		  $.each( data['plugins'], function( key, val ) {
			  htmlStr+='<tr><th colspan="2">Plugin: '+key+'</th></tr>';
			  $.each( val, function( key1, val1 ) {
				  if (typeof val1 === 'object') {
					  htmlStr+='<tr><td class="info">'+key1+'</td><td>'+dictToTable(val1)+'</td></tr>';
				  }else
					  htmlStr+='<tr><td class="info">'+key1+'</td><td>'+val1+'</td></tr>';
			  });
		  });
		  htmlStr+='<tr><th colspan="2">Logging</th></tr>';
		  $.each( data['logging'], function( key, val ) {
			  if (typeof val === 'object') {
				  htmlStr+='<tr><td class="info">'+key+'</td><td>'+JSON.stringify(val)+'</td></tr>';
			  }else
				  htmlStr+='<tr><td class="info">'+key+'</td><td>'+val+'</td></tr>';
		  });
		  htmlStr+='</table>';
		  $("#configdiv").html(htmlStr);
	  });
}

function dictToTable(obj){
	htmlStr='<table class="table">';
	$.each( obj, function( key, val ) {
		if (key!='password'&&key!='secret_access_key') {
			if (typeof val === 'object') 
				htmlStr+='<tr><td class="active">'+key+'</td><td>'+JSON.stringify(val)+'</td></tr>';
			else
				htmlStr+='<tr><td class="active">'+key+'</td><td>'+val+'</td></tr>';
		}
	});
	htmlStr+='</table>';
	return htmlStr;
}
function showServerStatus() {
	$.getJSON( "/server/status", function( data ) {
		console.log(data);
		htmlStr='<div class="panel-heading"><h3 class="panel-title">Runtime Status</h3></div><table class="table table-condensed"><tr><th class="info">Auto Mode</th><td>';
		htmlStr+=data['auto_mode']+'</td><td><button type="button" class="btn btn-success btn-sm" id="autobutton" data-whatever="'+data['auto_mode']+'">';
		if (data['auto_mode']==true) {
			htmlStr+="Disable";
		}else{
			htmlStr+="Enable";
		}
		htmlStr+='</button></td></tr><tr><th class="info">Cluster</th><td>'+dictToTable(data['cluster']);
//		$.each( data['cluster'], function( key, val ) {
//			htmlStr+='<b>'+key+'</b>: '+val+'; ';
//		});
		htmlStr+='</td><td>&nbsp;</td></tr></table>';
		$("#statusdiv").html(htmlStr);
		$('#autobutton').click(function() {
			var current_state = $(this).data('whatever');
			console.log(current_state);
			setAutoMode(!current_state);
		});
	});
}


function setAutoMode(auto_mode){
	req_type='PUT';
	if (auto_mode==false) {
		req_type='DELETE';
	}
	$.ajax({
        type: req_type,
        url: "/server/auto",
        success: function(response) {
		    console.log(response);
		    if (response["success"]==true){
		    	addAlert("success", "Successfully set auto node to "+auto_mode+".");
		    	showServerStatus();
		    }else
		    	addAlert("danger", "Failed to set auto node to "+auto_mode+".");
	    }
	});
	
}

initWNView();
