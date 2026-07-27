S3_BUCKET = detroit-election-maps
ACCOUNT_ID = 7718b66fac7dfe0e5badaa986de51a5d

all: tiles/precincts-2024/ tiles/precincts-2025/ tiles/precincts-2026/

# TODO: deploy-ckan-data
.PHONY: deploy-ckan-data
deploy-ckan-data:
	echo "TODO:"

.PHONY: deploy-results
deploy-results:
	aws --profile=detmaps \
		--endpoint-url https://$(ACCOUNT_ID).r2.cloudflarestorage.com \
		s3 sync ./data/output/ s3://$(S3_BUCKET)/results/ \
		--acl=public-read \
		--cache-control "public, max-age=0, must-revalidate"

.PHONY: deploy-tiles
deploy-tiles:
	aws --profile=detmaps \
		--endpoint-url https://$(ACCOUNT_ID).r2.cloudflarestorage.com \
		s3 sync ./tiles/ s3://$(S3_BUCKET)/tiles/ \
		--acl=public-read \
		--content-type application/vnd.mapbox-vector-tile \
    	--content-encoding gzip \
		--cache-control 'Cache-Control: "public, max-age=86400"'

data/output/2025/general/turnout.csv: data/output/2025/general/wayne/
	poetry run python scripts/combine_county_races.py data/output/2025/general

data/output/2024/primary/turnout.csv: data/output/2024/primary/wayne/ data/output/2024/primary/oakland/
	poetry run python scripts/combine_county_races.py data/output/2024/primary

data/output/2024/primary/oakland/: data/results/2024/oakland/primary.xml data/precincts/map-2024.json data/precincts/precincts-2024.geojson
	poetry run python scripts/process_oakland.py $< $@

data/output/2025/general/wayne/: data/results/2025/wayne/general.pdf
	poetry run python scripts/process_wayne_pdf.py $< $@

# TODO: set ID from state precincts
data/output/2024/primary/wayne/: data/precincts/map-2024.json data/results/2024/wayne/primary-state.pdf data/results/2024/wayne/primary-senate.pdf data/results/2024/wayne/primary-congress.pdf data/precincts/precincts-2024.geojson
	poetry run python scripts/process_wayne_alt_pdf.py data/results/2024/wayne/primary-state.pdf $@
	poetry run python scripts/process_wayne_alt_pdf.py data/results/2024/wayne/primary-senate.pdf $@
	poetry run python scripts/process_wayne_alt_pdf.py data/results/2024/wayne/primary-congress.pdf $@

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
	--use-attribute-for-id=id \
	--force \
	-L precincts:$< -o $@

# TODO: Other races
data/results/2024/wayne/primary-state.pdf:
	wget -qO $@ https://www.waynecountymi.gov/files/assets/mainsite/v/1/clerk/documents/elections/election-results/2024-august-6/strepa24_2.pdf

data/results/2024/wayne/primary-senate.pdf:
	wget -qO $@ https://www.waynecountymi.gov/files/assets/mainsite/v/1/clerk/documents/elections/election-results/2024-august-6/ussena24_1.pdf

data/results/2024/wayne/primary-congress.pdf:
	wget -qO $@ https://www.waynecountymi.gov/files/assets/mainsite/v/1/clerk/documents/elections/election-results/2024-august-6/conga24_1.pdf

data/results/2024/wayne/general.pdf:
	wget -qO $@ https://www.waynecountymi.gov/files/assets/mainsite/v/1/clerk/documents/elections/election-results/2024-november-5/partisan_offices.pdf

data/results/2025/wayne/general.pdf:
	wget -qO $@ https://www.waynecountymi.gov/files/assets/mainsite/v/1/clerk/documents/detpcts11425off.pdf

data/results/2025/wayne/primary.pdf:
	wget -qO $@ https://www.waynecountymi.gov/files/assets/mainsite/v/1/clerk/documents/elections/election-results/new-folder/detaug25pbpo.pdf

data/precincts/map-%.json: data/precincts/precincts-%.geojson
	cat $< | poetry run python scripts/process_precinct_map.py > $@

# TODO: There doesn't seem to be any overlap in non-zero padded values when converted to integers, but it's possible
data/precincts/precincts-2026.geojson:
	wget -qO - 'https://hub.arcgis.com/api/v3/datasets/b7df95c78668407280a7dead8e26aad0_0/downloads/data?format=geojson&spatialRefId=4326&where=1=1' | \
	npx mapshaper -i - filetype=geojson \
	-rename-fields id=NAME,precinct=PRECINCT,name=Precinct_Long_Name \
	-filter '["163", "125", "099"].includes(COUNTYFIPS)' \
	-filter-fields id,name \
	-each 'id = +id' \
	-o $@

data/precincts/precincts-2025.geojson:
	wget -qO - https://detroitdata.org/dataset/fb070cae-30b2-414e-a56a-7624e8a065e1/resource/cdff6247-8148-4ffb-8857-7ea31e80bbbd/download/cleaned_detroit_precincts_2025.geojson | \
	npx mapshaper -i - filetype=geojson \
	-rename-fields id=PRECINCT \
	-filter-fields id \
	-each 'id = +id.toString()' \
	-o $@

data/precincts/precincts-2024.geojson:
	wget -qO - 'https://hub.arcgis.com/api/v3/datasets/02d40893317d46569017beeb14f9c63e_9/downloads/data?format=geojson&spatialRefId=4326&where=1=1' | \
	npx mapshaper -i - filetype=geojson \
	-rename-fields id=NAME,precinct=PRECINCT,name=Precinct_Long_Name \
	-filter '["163", "125", "099"].includes(COUNTYFIPS) || (name || "").includes("Fenton")' \
	-filter '!!id && id !== "null"' \
	-filter-fields id,name \
	-each 'id = id.replace("A", "1").replace("B", "2").replace("C", "3")' \
	-each 'id = +id' \
	-o $@
