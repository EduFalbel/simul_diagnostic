BEGIN {
    # Records are separated by newlines
    RS = "\n"

    # Fields are separated by double quotes
    FS = "\""

    # split("", counter)
    split("", events)

    n = 1
}


function increment_counter(array, key) {
    # key in array ? array[key]++ : array[key] = 0
    array[key]++
}

function add_event(array, n, time, type, link_id, vehicle) {
    array[n]["time"] = time
    array[n]["type"] = type
    array[n]["link_id"] = link_id
    array[n]["vehicle"] = vehicle
}

# if ($4 == "entered link")
#     increment_counter(counter, $6)

# /"entered link"/ {increment_counter(counter, $6)}
/"entered link"/ {add_event(events, n, $2, $4, $6, $8) ; n++}
/"left link"/ {add_event(events, n, $2, $4, $6, $8) ; n++}
# /"entered link"/ {print $6}

END {
    # print "link_id,vehicle_count"
    # for (link_id in counter)
    #     printf "%d,%d\n", link_id, counter[link_id] 

    print "time,type,link_id,vehicle"
    for (event in events) {
        printf "%f,%s,%d,%d\n", events[event]["time"], events[event]["type"], events[event]["link_id"] , events[event]["vehicle"] 
    }
}
