from schema_obj import SchemaObject
import coloredlogs, logging
import sys

GENERIC_REPO_PATH = "C:\\local_ckp\\generic-entity-configuration"

if __name__ == '__main__':
    try:
        coloredlogs.install()
    except:
        print("Couldn't init coloredlogs. Continuing without")
    logging.basicConfig(level=logging.INFO)
    argv, argc = sys.argv, len(sys.argv)

    if argc < 3:
        logging.error("Not enough arguments!")
        print("USAGE: invdev create schema <url> <title>")
        print("OPTIONAL: --export-folder=<export-folder> --enrichment-url=<schema-title> --enrichment-title=<schema-title>")
        exit()


    url = argv[1]
    title_id = argv[2].lower()
    export_folder = [arg for arg in argv[3:] if arg.startswith('--export-folder=')]
    export_folder = export_folder[0][16:] if export_folder else ''
    enrichment_url = [arg for arg in argv[3:] if arg.startswith('--enrichment-url=')]
    enrichment_url = enrichment_url[0][17:] if enrichment_url else ''
    enrichment_title = [arg for arg in argv[3:] if arg.startswith('--enrichment-title=')]
    enrichment_title = enrichment_title[0][19:].lower() if enrichment_title else ''


    if export_folder == 'generic':
        export_folder = GENERIC_REPO_PATH + '\\azure_schemas_data'


    confirmation = input("Are you sure you want to create schema from url: {} with title_id: '{}': ".format(url, title_id)
                    + "\nWith Enrihcment url: {} and enrichment_title_id '{}'".format(enrichment_url if enrichment_title else 'NONE', enrichment_title if enrichment_title else 'NONE')
                    + "\nAnd export to: {} [Y/n] ".format(export_folder) )
    if not (confirmation.lower() == 'y' or confirmation.lower() == '') :
        exit()

    print('\nREMEMBER, this tool is totally not perfect, because it depends on the documentation shape of azure of which we dont have control.',
          '\nThus, MAKE SURE TO GO OVER the result schema and VERIFY it. Also take a look cli output of this command, as it can sometimes can give helpful feedback.',
          '\nHappy coding! ;0\n')

    try:
        SchemaObject.load_from_url(url, title_id, enrichment_url, enrichment_title, export_folder=export_folder)
    except:
        print('\n\n')
        logging.critical("Something failed.. idk anymore i wrote this code in 3am :(")