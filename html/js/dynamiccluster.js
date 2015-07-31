var frequency = 0;
var timer ;
function initWNView(){
	  $('#wntab').addClass('active');
	  $('#jtab').removeClass('active');
	  $('#rtab').removeClass('active');
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
					'<tr><th>Public DNS Name</th><td>'+data.instance.public_dns_name+'</td></tr>'+
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
	  $("#main").html('<div class="panel panel-default"><div class="panel-heading">Jobs</div><div class="table-responsive"><table class="table table-striped table-condensed"><thead><tr><th>Job Id</th><th>Name</th><th>State</th><th>Priority</th><th>Owner</th><th>Queue</th><th>Account</th><th>Property</th><th>Req. Walltime</th><th>Req. Mem</th><th>Req. Proc</th><th>Creation Time</th></tr></thead><tbody id="jtable"></tbody></table></div></div>');
	  $.getJSON( "/job", function( data ) {
		  var items = [];
		  var nodes = [];
		  //alert(data);
		  $.each( data, function( key, val ) {
			  //alert(val.id);
			  //console.log(val);
			  $('#jtable').append('<tr><th>'+val.jobid+'</th><td>'+val.name+'</td><td>'+convertJobState(val.state)+'</td><td>'+val.priority+'</td><td>'+val.owner+'</td><td>'+val.queue+'</td><td>'+val.account+'</td><td>'+val.property+'</td><td>'+val.requested_walltime+'</td><td>'+val.requested_mem+'</td><td>'+convertProc(val)+'</td><td>'+moment.unix(val.creation_time).format("YYYY-M-D h:mm:ss")+'</td><td>A</td></tr>'); 
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

function initResourceView() {
	  $('#wntab').removeClass('active');
	  $('#jtab').removeClass('active');
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
			  htmlstr+='<div style="padding: 3px; float: left; width: 70%; text-align: left;"><h5><span class="label label-primary">Type</span>'+val.type+' <span class="label label-primary">Min</span> '+val.min_num+' <span class="label label-primary">Current</span> '+val.current_num+' <span class="label label-primary">Max</span> '+val.max_num+'&nbsp;&nbsp;';
			  if (val.reservation_queue) htmlstr+='<span class="label label-success">Reservation</span><span class="label label-info">Queue</span>&nbsp;'+val.reservation_queue+'&nbsp;&nbsp;';
			  if (val.reservation_property) htmlstr+='<span class="label label-success">Reservation</span><span class="label label-info">Property</span>&nbsp;'+val.reservation_property+'&nbsp;&nbsp;';
			  if (val.reservation_account) htmlstr+='<span class="label label-success">Reservation</span><span class="label label-info">Account</span>&nbsp;'+val.reservation_account+'&nbsp;&nbsp;';
			  htmlstr+='<button type="button" class="btn btn-success btn-sm" id="addbutton'+val.name+'" data-toggle="modal" data-target="#addResDialog" data-whatever="'+val.name+'">Add</button></h5></div>';
			  percentage=parseInt(val.current_num*100/val.max_num);
			  htmlstr+='<div class="progress"><div class="progress-bar" role="progressbar" aria-valuenow="'+percentage+'" aria-valuemin="0" aria-valuemax="100" style="width: '+percentage+'%;">'+percentage+'%</div></div></div>';
			  htmlstr+='<table class="table table-striped table-condensed"><thead><tr><th>Hostname</th><th>Instance Name</th><th>VCPUS</th><th>State</th><th>IP</th><th>State In Cloud</th><th>Jobs</th></tr></thead><tbody>';
			  $.each(val.worker_nodes, function(key1, val1){
				  console.log(val1);
				  jobs='';
				  if (val1.jobs) jobs=val1.jobs;
				  htmlstr+='<tr><th><a href=\'javascript:showWorkerNode("'+val1.hostname+'")\'>'+val1.hostname+'</a></th><td>'+val1.instance.instance_name+'</td><td>'+val1.num_proc+'</td><td>'+convertWNState(val1.state)+'</td><td>'+val1.instance.ip+'</td><td>'+convertCloudState(val1.instance.state)+'</td><td>'+jobs+'</td></tr>';
			  });
			  htmlstr+='</tbody></table></div></div>';
		  });
		  htmlstr+='</div>';
		  //console.log(htmlstr);
		  $("#main").html(htmlstr);
		});
}

function addResource(res_name, num){
	console.log(res_name+" "+n);
	$.ajax({
        type: "PUT",
        url: "/resource/"+res_name+"?num="+num,
        success: function(response) {
	    console.log(response);
	    if (response["success"]==true){
	    	$("#successalert").show();
	    	initResourceView();
	    }else
	    	$("#failalert").show();
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

initWNView();
