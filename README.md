# AzureSchemaify
A tool to convert the doc page of azure REST API to a JSON schema.  

## Installation

1. Install the latest verstion of [python](https://www.python.org/downloads/). Make sure to add it to path ;).
2. Clone the repo: `git clone https://github.com/ShakedAp/AzureSchemaify.git`
3. Install the dependencies: `pip install -r requirements.txt`
4. OPTIONAL: Update the `GENERIC_REPO_PATH` of the repo in the `create_schema.py` file

## Usage

In order to use the tool run:  
`python create_schema.py <schema-url> <property-name>`  
  
Optional properties:  
`--export-folder=` Export path. Use `--export-folder=generic` in order to export to the generic entity folder. Leave empty to export to the current folder  
`--enrichment-url=` Enrichment url  
`--enrichment-title=` Enrichment title  
_Enrichment support is a bit naive right now, so make sure to update it to be correct afterwards_  

### Examples

Create a single schema:  
```
python create_schema.py "https://learn.microsoft.com/en-us/rest/api/batchmanagement/batch-account/list?view=rest-batchmanagement-2023-11-01&tabs=HTTP" BatchAccount
```
Create a schema + enrichment:  
```
python create_schema.py "https://learn.microsoft.com/en-us/rest/api/batchmanagement/batch-account/list?view=rest-batchmanagement-2023-11-01&tabs=HTTP" BatchAccount
       --enrichment-url="https://learn.microsoft.com/en-us/rest/api/batchmanagement/pool/list-by-batch-account?view=rest-batchmanagement-2023-11-01&tabs=HTTP" --enrichment-title=Pool
```
