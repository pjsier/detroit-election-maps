S3_BUCKET = detroit-election-maps
ACCOUNT_ID = 7718b66fac7dfe0e5badaa986de51a5d

all: tiles/precincts-2024/

.PHONY: deploy-results
deploy-results:
	aws --profile=detmaps \
		--endpoint-url https://$(ACCOUNT_ID).r2.cloudflarestorage.com \
		s3 sync ./deploy-output/ s3://$(S3_BUCKET)/results/ \
		--acl=public-read \
		--content-encoding gzip \
		--cache-control "public, max-age=0, must-revalidate"

.PHONY: deploy-tiles
deploy-tiles:
	aws --profile=detmaps \
		--endpoint-url https://$(ACCOUNT_ID).r2.cloudflarestorage.com \
		s3 sync ./tiles/ s3://$(S3_BUCKET)/tiles/ \
		--acl=public-read \
		--content-encoding gzip \
		--cache-control 'Cache-Control: "public, max-age=86400"'

# GZIP-compress output before it's synced with s3cmd
.PHONY: build-output
build-output:
	mkdir -p deploy-output
	cp -r data/output/* deploy-output
	find deploy-output -type f -exec gzip -9 {} \; -exec mv {}.gz {} \;

data/output/%/: data/elections/%.xlsx data/elections/%-turnout.json
	poetry run python scripts/process_results.py $<
	poetry run python scripts/process_turnout.py $(filter-out $<,$^)

tiles/%/: data/precincts/%.mbtiles
	mkdir -p $@
	tile-join --no-tile-size-limit --force -e $@ $<

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
