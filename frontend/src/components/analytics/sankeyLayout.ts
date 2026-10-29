export interface SankeyNode {
  name: string;
  color?: string | null;
  value?: number;
  category_id?: number;
}

export interface SankeyLink {
  source: number;
  target: number;
  value: number;
  color?: string;
}

export interface SankeyData {
  nodes: SankeyNode[];
  links: SankeyLink[];
}


// Layout maison (au lieu du <Sankey> de recharts) : recharts envoie tous les nœuds terminaux
// dans la dernière colonne, si bien que les flux Épargne / Investissements traversaient la
// colonne des groupes, et sa relaxation itérative croisait les liens. Ici le placement est
// déterministe : chaque nœud reste à sa profondeur naturelle, les colonnes sont ordonnées
// d'après leurs parents et les enfants descendent en cascade sous leur parent.
export const DEFAULT_MARGIN = { top: 16, right: 170, bottom: 16, left: 16 };
// Écran étroit : marge droite réduite (libellés plus courts, coupés au besoin) pour laisser de la place aux flux
export const NARROW_WIDTH = 520;
export const MARGIN_NARROW = { top: 12, right: 92, bottom: 12, left: 10 };
export const NODE_WIDTH = 4;
export const LABEL_HEIGHT = 30; // hauteur réservée à un libellé de deux lignes
export const NODE_GAP = 8;
export const MAIN_COLUMN_HEIGHT = 320; // hauteur visée pour la colonne la plus chargée
export const DEFAULT_COLOR = "#94a3b8";

export interface LaidNode {
  index: number;
  name: string;
  color: string;
  value: number;
  depth: number;
  x: number;
  y: number; // haut de la barre
  height: number;
}

export interface LaidLink {
  index: number;
  source: LaidNode;
  target: LaidNode;
  value: number;
  width: number;
  sy: number; // centre du lien côté source
  ty: number; // centre du lien côté cible
}

export function computeLayout(data: SankeyData, width: number) {
  const MARGIN = width < NARROW_WIDTH ? MARGIN_NARROW : DEFAULT_MARGIN;
  const n = data.nodes.length;
  const links = data.links.filter((l) => l.value > 0 && l.source < n && l.target < n);
  const outLinks: number[][] = Array.from({ length: n }, () => []);
  const inLinks: number[][] = Array.from({ length: n }, () => []);
  links.forEach((l, i) => {
    outLinks[l.source].push(i);
    inLinks[l.target].push(i);
  });

  const used = data.nodes.map((_, i) => outLinks[i].length + inLinks[i].length > 0);
  const inSum = inLinks.map((ls) => ls.reduce((s, i) => s + links[i].value, 0));
  const outSum = outLinks.map((ls) => ls.reduce((s, i) => s + links[i].value, 0));
  const value = data.nodes.map((_, i) => Math.max(inSum[i], outSum[i]));

  // Profondeur = plus long chemin depuis une source (borné en cas de cycle)
  const depth = new Array(n).fill(0);
  for (let pass = 0; pass < n; pass++) {
    let changed = false;
    for (const l of links) {
      if (depth[l.target] < depth[l.source] + 1) {
        depth[l.target] = depth[l.source] + 1;
        changed = true;
      }
    }
    if (!changed) break;
  }
  const maxDepth = Math.max(1, ...depth.filter((_, i) => used[i]));
  const columns: number[][] = Array.from({ length: maxDepth + 1 }, () => []);
  data.nodes.forEach((_, i) => used[i] && columns[depth[i]].push(i));

  const maxColumnValue = Math.max(
    1,
    ...columns.map((col) => col.reduce((s, i) => s + value[i], 0)),
  );
  const k = MAIN_COLUMN_HEIGHT / maxColumnValue;
  const barHeight = (i: number) => Math.max(value[i] * k, 2);
  const slotHeight = (i: number) => Math.max(barHeight(i), LABEL_HEIGHT);

  const columnStep = (width - MARGIN.left - MARGIN.right - NODE_WIDTH) / maxDepth;
  const rank = new Array(n).fill(0);
  const y = new Array(n).fill(0);

  // Décalage (centre) d'un lien dans la barre source : liens triés par colonne puis rang de la cible.
  const sourceOffset = (linkIdx: number) => {
    const l = links[linkIdx];
    const sorted = [...outLinks[l.source]].sort(
      (a, b) => depth[links[a].target] - depth[links[b].target] || rank[links[a].target] - rank[links[b].target],
    );
    let offset = (barHeight(l.source) - outSum[l.source] * k) / 2;
    for (const i of sorted) {
      const w = links[i].value * k;
      if (i === linkIdx) return offset + w / 2;
      offset += w;
    }
    return offset;
  };

  columns.forEach((col, c) => {
    if (c === 0) {
      col.sort((a, b) => value[b] - value[a]);
    } else {
      // Ordre hérité du parent principal (le plus haut), puis ordre des liens fourni par l'API
      const key = (i: number) => {
        const first = [...inLinks[i]].sort((a, b) => y[links[a].source] - y[links[b].source])[0];
        const parent = links[first].source;
        return [y[parent], outLinks[parent].indexOf(first)];
      };
      const keys = new Map(col.map((i) => [i, key(i)]));
      col.sort((a, b) => keys.get(a)![0] - keys.get(b)![0] || keys.get(a)![1] - keys.get(b)![1]);
    }
    col.forEach((i, r) => (rank[i] = r));

    let cursor = MARGIN.top;
    for (const i of col) {
      const slot = slotHeight(i);
      let desiredTop = cursor;
      if (c > 0) {
        // Centré sur l'arrivée de ses flux entrants, sans jamais remonter au-dessus du voisin
        const total = inSum[i] || 1;
        const center = inLinks[i].reduce(
          (s, li) => s + (y[links[li].source] + sourceOffset(li)) * links[li].value,
          0,
        ) / total;
        desiredTop = center - slot / 2;
      }
      const top = Math.max(desiredTop, cursor);
      y[i] = top + (slot - barHeight(i)) / 2;
      cursor = top + slot + NODE_GAP;
    }
  });

  const laidNodes: LaidNode[] = data.nodes.map((node, i) => ({
    index: i,
    name: node.name,
    color: node.color || DEFAULT_COLOR,
    value: value[i],
    depth: depth[i],
    x: MARGIN.left + depth[i] * columnStep,
    y: y[i],
    height: barHeight(i),
  }));

  const laidLinks: LaidLink[] = links.map((l, i) => {
    const sorted = [...inLinks[l.target]].sort((a, b) => y[links[a].source] - y[links[b].source]);
    let offset = (barHeight(l.target) - inSum[l.target] * k) / 2;
    for (const j of sorted) {
      if (j === i) break;
      offset += links[j].value * k;
    }
    const w = l.value * k;
    return {
      index: i,
      source: laidNodes[l.source],
      target: laidNodes[l.target],
      value: l.value,
      width: w,
      sy: y[l.source] + sourceOffset(i),
      ty: y[l.target] + offset + w / 2,
    };
  });

  const bottom = Math.max(
    ...laidNodes.filter((_, i) => used[i]).map((nd) => nd.y + nd.height / 2 + LABEL_HEIGHT / 2),
  );

  return {
    nodes: laidNodes.filter((_, i) => used[i]),
    links: laidLinks,
    height: Math.max(240, bottom + MARGIN.bottom),
    narrow: width < NARROW_WIDTH,
  };
}
