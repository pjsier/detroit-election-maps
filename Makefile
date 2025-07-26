data/output/%/: data/elections/%.xlsx data/elections/%-turnout.json
	poetry run python scripts/process_results.py $<
	poetry run python scripts/process_turnout.py $(filter-out $<,$^)

data/precincts/%.pmtiles: data/precincts/%.mbtiles
	pmtiles convert $< $@

.PRECIOUS:
data/precincts/%.mbtiles: data/precincts/%.geojson
	tippecanoe \
	--simplification=10 \
	--simplify-only-low-zooms \
	--minimum-zoom=5 \
	--maximum-zoom=12 \
	--no-tile-stats \
	--detect-shared-borders \
	--grid-low-zooms \
	--coalesce-smallest-as-needed \
	--attribute-type=id:string \
	--use-attribute-for-id=id \
	--force \
	-L precincts:$< -o $@

data/precincts/precincts-2024.geojson:
	wget -qO - 'https://data.detroitmi.gov/api/download/v1/items/5d861ef3ba5a43e88dad58062b99f571/geojson?layers=0' | \
	mapshaper -i - filetype=geojson \
	-proj from=EPSG:3857 crs=EPSG:4326 \
	-rename-fields id=election_precinct \
	-filter-fields id \
	-each 'id = id.toString()' \
	-clean snap-interval=0.0005 \
	-o $@
