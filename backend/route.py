from math import radians, sin, cos, sqrt, atan2

def haversine(lat1, lon1, lat2, lon2):
    # calculeaza distanta in linie dreapta intre 2 puncte GPS, in km
    # (tine cont ca Pamantul e o sfera, nu foloseste geometrie plana simpla)
    R = 6371  # raza Pamantului, in km

    # diferenta dintre punctele, convertita din grade in radiani
    # (functiile trigonometrice din Python lucreaza in radiani)
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    # formula Haversine - parte intermediara de calcul
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2

    # rezultatul final: distanta in km
    return R * 2 * atan2(sqrt(a), sqrt(1-a))


def nearest_neighbour(depot, points):
    """
    depot: (lat, lon) - punctul de start/final
    points: dict {container_id: (lat, lon)}
    Returneaza: lista ordonata de container_id-uri
    """
    # copie a punctelor ramase de vizitat - "consumam" din ea pe masura ce avansam
    remaining = dict(points)
    route = []
    current = depot  # pornim din depou

    while remaining:
        # gasim, dintre punctele ramase, cel mai apropiat de pozitia curenta
        nearest_id = min(
            remaining,
            key=lambda cid: haversine(current[0], current[1], remaining[cid][0], remaining[cid][1])
        )

        route.append(nearest_id)      # il adaugam in traseu
        current = remaining[nearest_id]  # ne "mutam" acolo
        del remaining[nearest_id]     # il scoatem din lista de vizitat

    return route


def route_distance(depot, route, points):
    """Calculeaza distanta totala a unui traseu complet (depot -> ... -> depot)."""
    total = 0
    current = depot

    # adunam distanta intre fiecare 2 opriri consecutive din traseu
    for cid in route:
        total += haversine(current[0], current[1], points[cid][0], points[cid][1])
        current = points[cid]

    # adaugam si drumul de intoarcere, de la ultima oprire inapoi la depou
    total += haversine(current[0], current[1], depot[0], depot[1])

    return total


def two_opt(depot, route, points):
    """Imbunatateste ordinea, incercand sa elimine intersectii."""
    best = route[:]  # copie a traseului curent, cel mai bun gasit pana acum
    best_distance = route_distance(depot, best, points)
    improved = True

    # repetam cat timp mai gasim imbunatatiri
    while improved:
        improved = False

        # incercam toate perechile posibile de pozitii (i, j) din traseu
        for i in range(len(best) - 1):
            for j in range(i + 1, len(best)):
                # "taiem" traseul intre i si j, inversam bucata din mijloc,
                # si vedem daca noul traseu e mai scurt
                new_route = best[:i] + best[i:j+1][::-1] + best[j+1:]
                new_distance = route_distance(depot, new_route, points)

                if new_distance < best_distance:
                    best = new_route
                    best_distance = new_distance
                    improved = True  # am gasit o imbunatatire, mai incercam o tura

    return best, best_distance