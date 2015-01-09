var frequency = 0;
var timer ;
function initWNView(){
	  $('#wntab').addClass('active');
	  $('#jtab').removeClass('active');
	  $("#main").html('<div class="panel panel-default"><div class="panel-heading">Worker Nodes</div><table class="table"><thead><tr><th>Hostname</th><th>Type</th><th>Proc Num</th><th>State</th><th>Time in current state</th><th>Jobs</th><th>Attributes</th></tr></thead><tbody id="wntable"></tbody></table></div>');
	  $.getJSON( "/workernode", function( data ) {
		  var items = [];
		  var nodes = [];
		  //alert(data);
		  $.each( data, function( key, val ) {
			  //alert(val.id);
			  //console.log(val);
			  $('#wntable').append('<tr><th>'+val.hostname+'</th><td>'+val.type+'</td><td>'+val.num_proc+'</td><td>'+convertWNState(val.state)+'</td><td>'+convertTimeInCurrentState(val.time_in_current_state)+'</td><td>'+val.jobs+'</td><td>A</td></tr>'); 
		  });
		});
}

function convertTimeInCurrentState(t) {
	if (t/60>0) {
		return parseInt(t/60)+"m"+parseInt(t%60)+"s";
	}
	return parseInt(t)+"s";
}

function convertWNState(s) { 
	if (s==1) return "Starting";
	if (s==2) return "Configuring";
	if (s==3) return "Idle";
	if (s==4) return "Busy";
	if (s==5) return "Error";
	if (s==6) return "Deleting";
	return "Inexistent";
}

function initJobView(){
	  $('#wntab').removeClass('active');
	  $('#jtab').addClass('active');
	  $("#main").html('<div class="panel panel-default"><div class="panel-heading">Jobs</div><table class="table"><thead><tr><th>Job Id</th><th>Name</th><th>State</th><th>Priority</th><th>Owner</th><th>Queue</th><th>Account String</th><th>Req. Walltime</th><th>Req. Mem</th><th>Req. Proc</th><th>Creation Time</th></tr></thead><tbody id="jtable"></tbody></table></div>');
	  $.getJSON( "/job", function( data ) {
		  var items = [];
		  var nodes = [];
		  //alert(data);
		  $.each( data, function( key, val ) {
			  //alert(val.id);
			  //console.log(val);
			  $('#jtable').append('<tr><th>'+val.jobid+'</th><td>'+val.name+'</td><td>'+convertJobState(val.state)+'</td><td>'+val.priority+'</td><td>'+val.owner+'</td><td>'+val.queue+'</td><td>'+val.account_string+'</td><td>'+val.requested_walltime+'</td><td>'+val.requested_mem+'</td><td>'+convertProc(val.requested_proc)+'</td><td>'+moment.unix(val.creation_time).format("YYYY-M-D h:mm:ss")+'</td><td>A</td></tr>'); 
		  });
		});
}

function convertJobState(s) {
	if (s==0) return "Queued";
	if (s==1) return "Running";
	return "Other";
}

function convertProc(p) {
	return p.num_cores+"cores*"+p.num_nodes+"nodes";
}

initWNView();
