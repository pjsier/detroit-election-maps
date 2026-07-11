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

# TODO: set ID from state precincts
data/output/2024/primary/: data/results/2024/primary-state.pdf data/results/2024/primary-senate.pdf data/results/2024/primary-congress.pdf
	poetry run python scripts/process_wayne_alt_pdf.py data/results/2024/primary-state.pdf $@
	poetry run python scripts/process_wayne_alt_pdf.py data/results/2024/primary-senate.pdf $@
	poetry run python scripts/process_wayne_alt_pdf.py data/results/2024/primary-congress.pdf $@

data/output/%/: data/results/%.pdf
	poetry run python scripts/process_wayne_pdf.py $< $@

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

# TODO: Other races
data/results/2024/primary-state.pdf:
	wget -qO $@ https://www.waynecountymi.gov/files/assets/mainsite/v/1/clerk/documents/elections/election-results/2024-august-6/strepa24_2.pdf

data/results/2024/primary-senate.pdf:
	wget -qO $@ https://www.waynecountymi.gov/files/assets/mainsite/v/1/clerk/documents/elections/election-results/2024-august-6/ussena24_1.pdf

data/results/2024/primary-congress.pdf:
	wget -qO $@ https://www.waynecountymi.gov/files/assets/mainsite/v/1/clerk/documents/elections/election-results/2024-august-6/conga24_1.pdf

data/results/2024/general.pdf:
	wget -qO $@ https://www.waynecountymi.gov/files/assets/mainsite/v/1/clerk/documents/elections/election-results/2024-november-5/partisan_offices.pdf

data/results/2025/general.pdf:
	wget -qO $@ https://www.waynecountymi.gov/files/assets/mainsite/v/1/clerk/documents/detpcts11425off.pdf

data/results/2025/primary.pdf:
	wget -qO $@ https://www.waynecountymi.gov/files/assets/mainsite/v/1/clerk/documents/elections/election-results/new-folder/detaug25pbpo.pdf

data/precincts/mi-precincts-2024.geojson:
	wget -qO - 'https://hub.arcgis.com/api/v3/datasets/02d40893317d46569017beeb14f9c63e_9/downloads/data?format=geojson&spatialRefId=4326&where=1=1' | \
	npx mapshaper -i - filetype=geojson \
	-rename-fields id=NAME \
	-filter '["163", "125", "099"].includes(COUNTYFIPS)' \
	-o $@

data/precincts/precincts-2024.geojson:
	wget -qO - https://detroitdata.org/dataset/fb070cae-30b2-414e-a56a-7624e8a065e1/resource/cdff6247-8148-4ffb-8857-7ea31e80bbbd/download/cleaned_detroit_precincts_2025.geojson | \
	npx mapshaper -i - filetype=geojson \
	-rename-fields id=PRECINCT \
	-filter-fields id \
	-each 'id = +id.toString()' \
	-o $@