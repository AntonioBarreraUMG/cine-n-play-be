SELECT table_schema, table_name, column_name, column_default, is_identity, identity_generation
FROM information_schema.columns
WHERE table_schema = 'public'
  AND ((table_name = 'peliculas' AND column_name = 'id_pelicula')
    OR (table_name = 'videojuegos' AND column_name = 'id_videojuego'));

SELECT tc.table_name, tc.constraint_type, kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name AND tc.constraint_schema = kcu.constraint_schema
  AND tc.table_name = kcu.table_name
WHERE tc.table_schema = 'public'
  AND tc.table_name IN ('peliculas','videojuegos')
  AND tc.constraint_type = 'PRIMARY KEY';
