-- Solo lectura. Compartir el resultado, sin credenciales.
SELECT table_schema, table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
  AND (table_name ILIKE '%pelicul%' OR table_name ILIKE '%videojueg%')
ORDER BY table_schema, table_name, ordinal_position;
