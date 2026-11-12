/** Objet partiel présenté comme `T` : pour passer à un composant un contexte dont seuls certains champs servent au test. */
export const partial = <T>(value: Partial<T>): T => value as T
