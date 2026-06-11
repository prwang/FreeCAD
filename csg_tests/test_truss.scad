// 2D truss frame profile WITHOUT hull()
// OpenSCAD units are mm by convention

CIRCLE_OD  = 8;
CIRCLE_ID  = 4;
TRUSS_WID  = 4;
FILLET_RAD = 1.5;

$fn = 64;

// Hole center coordinates
pts = [
    [0, 0],
    [0, 30],
    [40, 0]
];

// Connectivity between points by index
edges = [
    [0, 1],
    [1, 2],
    [2, 0]
];

function dist(a, b) =
    sqrt((b[0] - a[0]) * (b[0] - a[0]) +
         (b[1] - a[1]) * (b[1] - a[1]));

function angle_between(a, b) =
    atan2(b[1] - a[1], b[0] - a[0]);

module truss_member_rect(a, b, wid) {
    mid = [
        (a[0] + b[0]) / 2,
        (a[1] + b[1]) / 2
    ];

    translate(mid)
        rotate(angle_between(a, b))
            square([dist(a, b), wid], center = true);
}

module raw_truss_frame(points, connections, circle_od, circle_id, truss_wid) {
    difference() {
        union() {
            // Rectangular truss members, centered on hole centers
            for (e = connections) {
                truss_member_rect(
                    points[e[0]],
                    points[e[1]],
                    truss_wid
                );
            }

            // Outer circular bosses
            for (p = points) {
                translate(p)
                    circle(d = circle_od);
            }
        }

        // Holes
        for (p = points) {
            translate(p)
                circle(d = circle_id);
        }
    }
}

module truss_frame(points, connections, circle_od, circle_id, truss_wid, fillet_rad) {
    offset(r = -fillet_rad) offset(r = fillet_rad)
            raw_truss_frame(
                points,
                connections,
                circle_od,
                circle_id,
                truss_wid
            );
}

truss_frame(
    points      = pts,
    connections = edges,
    circle_od   = CIRCLE_OD,
    circle_id   = CIRCLE_ID,
    truss_wid   = TRUSS_WID,
    fillet_rad  = FILLET_RAD
);