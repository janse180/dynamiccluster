schedule:
  collect_load_avg:
    function: collector.collect_load_avg
    seconds: 10
    returner: zeromq
