// FreeCAD-friendly 2D truss profile
// Avoids top-level union()
// Avoids hull()
// Uses De Morgan union:
// A OR B = NOT(NOT(A) AND NOT(B))
// Also nests intersection() one-by-one only.

CIRCLE_OD  = 8;
CIRCLE_ID  = 4;
TRUSS_WID  = 4;
FILLET_RAD = 1;

// Extra safety margin for the finite universal set
UNIVERSAL_PAD = 20;

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

function min_x(points) = min([for (p = points) p[0]]);
function max_x(points) = max([for (p = points) p[0]]);
function min_y(points) = min([for (p = points) p[1]]);
function max_y(points) = max([for (p = points) p[1]]);

function universal_pad(circle_od, truss_wid, fillet_rad) =
    max([circle_od, truss_wid]) / 2
    + 2 * fillet_rad
    + UNIVERSAL_PAD;

module universal_set(points, circle_od, truss_wid, fillet_rad) {
    pad = universal_pad(circle_od, truss_wid, fillet_rad);

    translate([
        min_x(points) - pad,
        min_y(points) - pad
    ])
        square([
            max_x(points) - min_x(points) + 2 * pad,
            max_y(points) - min_y(points) + 2 * pad
        ]);
}

module truss_member_rect(a, b, wid) {
    mid = [
        (a[0] + b[0]) / 2,
        (a[1] + b[1]) / 2
    ];

    translate(mid)
        rotate(angle_between(a, b))
            square([dist(a, b), wid], center = true);
}

// One positive primitive at a time:
// idx 0..len(edges)-1 are rectangular members
// idx len(edges)..len(edges)+len(points)-1 are outer circular bosses
module positive_shape_by_index(idx, points, connections, circle_od, truss_wid) {
    n_edges = len(connections);

    if (idx < n_edges) {
        e = connections[idx];

        truss_member_rect(
            points[e[0]],
            points[e[1]],
            truss_wid
        );
    } else {
        pidx = idx - n_edges;

        translate(points[pidx])
            circle(d = circle_od);
    }
}

// NOT(shape), clipped to the finite universal set
module complement_positive_shape_by_index(
    idx,
    points,
    connections,
    circle_od,
    truss_wid,
    fillet_rad
) {
    difference() {
        universal_set(points, circle_od, truss_wid, fillet_rad);

        positive_shape_by_index(
            idx,
            points,
            connections,
            circle_od,
            truss_wid
        );
    }
}

// Binary / recursive intersection only:
// intersection(
//     complement(shape_i),
//     intersection(
//         complement(shape_i+1),
//         ...
//     )
// )
module intersect_complements_one_by_one(
    idx,
    count,
    points,
    connections,
    circle_od,
    truss_wid,
    fillet_rad
) {
    if (idx == count - 1) {
        complement_positive_shape_by_index(
            idx,
            points,
            connections,
            circle_od,
            truss_wid,
            fillet_rad
        );
    } else {
        intersection() {
            complement_positive_shape_by_index(
                idx,
                points,
                connections,
                circle_od,
                truss_wid,
                fillet_rad
            );

            intersect_complements_one_by_one(
                idx + 1,
                count,
                points,
                connections,
                circle_od,
                truss_wid,
                fillet_rad
            );
        }
    }
}

// De Morgan union of all positive primitives:
// union(shapes...) = U - intersection(U - shape_0, U - shape_1, ...)
module demorgan_positive_union(
    points,
    connections,
    circle_od,
    truss_wid,
    fillet_rad
) {
    count = len(connections) + len(points);

    if (count == 1) {
        positive_shape_by_index(
            0,
            points,
            connections,
            circle_od,
            truss_wid
        );
    } else {
        difference() {
            universal_set(points, circle_od, truss_wid, fillet_rad);

            intersect_complements_one_by_one(
                0,
                count,
                points,
                connections,
                circle_od,
                truss_wid,
                fillet_rad
            );
        }
    }
}

// Subtract holes one-by-one, also avoiding multi-child difference
module subtract_holes_one_by_one(
    idx,
    points,
    connections,
    circle_od,
    circle_id,
    truss_wid,
    fillet_rad
) {
    if (idx == len(points)) {
        demorgan_positive_union(
            points,
            connections,
            circle_od,
            truss_wid,
            fillet_rad
        );
    } else {
        difference() {
            subtract_holes_one_by_one(
                idx + 1,
                points,
                connections,
                circle_od,
                circle_id,
                truss_wid,
                fillet_rad
            );

            translate(points[idx])
                circle(d = circle_id);
        }
    }
}

module raw_truss_frame(
    points,
    connections,
    circle_od,
    circle_id,
    truss_wid,
    fillet_rad
) {
    subtract_holes_one_by_one(
        0,
        points,
        connections,
        circle_od,
        circle_id,
        truss_wid,
        fillet_rad
    );
}

module truss_frame(
    points,
    connections,
    circle_od,
    circle_id,
    truss_wid,
    fillet_rad
) {
    offset(r = -fillet_rad)
        offset(r = fillet_rad)
            raw_truss_frame(
                points,
                connections,
                circle_od,
                circle_id,
                truss_wid,
                fillet_rad
            );
}

// Single top-level object
truss_frame(
    points      = pts,
    connections = edges,
    circle_od   = CIRCLE_OD,
    circle_id   = CIRCLE_ID,
    truss_wid   = TRUSS_WID,
    fillet_rad  = FILLET_RAD
);