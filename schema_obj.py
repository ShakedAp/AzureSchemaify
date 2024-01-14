from enum import Enum
from typing import List
import os
import json
import re
import logging
from bs4 import BeautifulSoup 
from selenium import webdriver


class SchemaObjectType(Enum):
    STRING = 0
    NUMBER = 1
    INTEGER = 2,
    OBJECT = 3,
    ARRAY = 4,
    BOOLEAN = 5,
    NULL = 6

def _string_to_schema_type(type_: str):
    _type_ = type_.lower()
    if _type_ == 'string':
        return SchemaObjectType.STRING
    elif _type_ == 'number':
        return SchemaObjectType.NUMBER
    elif _type_ == 'integer':
        return SchemaObjectType.INTEGER
    elif _type_ == 'object':
        return SchemaObjectType.OBJECT
    elif _type_ == 'array':
        return SchemaObjectType.ARRAY
    elif _type_ == 'boolean':
        return SchemaObjectType.BOOLEAN

    logging.warning(f"couldn't parse type: '{type_}' so returning NULL")
    return SchemaObjectType.NULL

def _schema_type_to_string(type_: SchemaObjectType):
    if type_ == SchemaObjectType.STRING:
        return 'string'
    elif type_ == SchemaObjectType.NUMBER:
        return 'number'
    elif type_ == SchemaObjectType.INTEGER:
        return 'integer'
    elif type_ == SchemaObjectType.BOOLEAN:
        return 'boolean'
    elif type_ == SchemaObjectType.ARRAY:
        return 'array'
    elif type_ == SchemaObjectType.OBJECT:
        return 'object'
    
    return 'null'
       
def _is_table_enum(soup: BeautifulSoup, title_id: str) -> str:
    title_obj = soup.find("h3", {"id": title_id})
    title = title_obj.text.strip()
    table = soup.find(lambda tag: tag.name == "table" and "aria-label" in tag.attrs and tag.attrs["aria-label"] == title)
    if not table:
        table = title_obj.find_next('table')
    if not table:
        return _schema_type_to_string(SchemaObjectType.NULL)
    
    rows = table.find_all('tr')

    return_type = 'false'
    for row in rows[1:]:
        cols = row.find_all('td')
        if len(cols) < 2:
            continue

        if len(cols) == 3:
            name, type_, desc = [el.text.strip() for el in cols]
        if len(cols) == 4:
            name, type_, default_value, desc = [el.text.strip() for el in cols]

        if desc and not name[0].isupper():
            return 'false'
        else:
            return_type = type_
    
    return return_type

def _handle_objects(soup: BeautifulSoup, name: str, link: str, parent_link_path: List[str], default_value: str = '') -> bool:
    if link in parent_link_path: # huh! stop the recursion
        logging.warning(f"stopped recursion for '{name}', in path: {parent_link_path}\nCreating an empty object instead")
        return SchemaObject(name, SchemaObjectType.OBJECT, [])

    try:
        enum_type = _is_table_enum(soup, link)
    except Exception as e:
        logging.error(f"couldn't parse object with id: '{link}', and find out if its an enum\nCreating an empty object instead")
        return SchemaObject(name, SchemaObjectType.OBJECT, [])

    if enum_type == 'false':
        schema_obj = SchemaObject.load_from_page(soup, link, parent_link_path)
        schema_obj.name = name

        return schema_obj
    else:
        return SchemaObject(name, _string_to_schema_type(enum_type), [], default_value=default_value)

def _add_obj_schemaobject_path(schema_obj: 'SchemaObject', add_obj: 'SchemaObject' , path: List[str], link_path: List[str]):
    if not path:
        add_obj.link_path.extend(link_path)
        schema_obj.properties.append(add_obj)
        return


    new_link_path = link_path.copy()
    new_link_path.append(path[0])
    # if there are duplicates, it adds to the first
    for p in schema_obj.properties: 
        if p.name == path[0]:
            _add_obj_schemaobject_path(p, add_obj, path[1:], new_link_path)
            return

    # Create new
    new_schema_obj = SchemaObject(path[0], SchemaObjectType.OBJECT, [], new_link_path)
    schema_obj.properties.append(new_schema_obj)
    _add_obj_schemaobject_path(new_schema_obj, add_obj, path[1:], new_link_path)

def _create_schema_object_recursive(soup: BeautifulSoup, name: str, type_: str, default_value: str, 
                                    desc: str, link: str, parent_link_path: List[str]):
    if not re.match(r'[a-zA-Z0-9\[\]]+$', type_):
        logging.error(f"found a weird type for '{name}', the type is {type_}.\nCreating an object with the type NULL. Please modify it yourself")
        return SchemaObject(name, SchemaObjectType.NULL, [])
    elif type_[-2:] == '[]':
        schema_arr = SchemaObject(name, SchemaObjectType.ARRAY, [])
        if link:
            # when parsing ignore the name ;)
            schema_arr.properties.append(_handle_objects(soup, name, link, parent_link_path)) 
        else:
            schema_arr.properties.append(SchemaObject('', _string_to_schema_type(type_[:-2]), [], parent_link_path))
        return schema_arr
    elif link: 
        return _handle_objects(soup, name, link, parent_link_path, default_value)
    else:
        return SchemaObject(name, _string_to_schema_type(type_), [], default_value=default_value)

class SchemaObject:

    def __init__(self, name: str, type_: SchemaObjectType, properties: List['SchemaObject'], 
                 link_path: List[str] = None, default_value: str='') -> None:
        self.name = name
        self.type = type_
        self.properties = properties
        self.default_value = default_value
        if not link_path:
            self.link_path = []
        else:
            self.link_path = link_path # this is done by reference!

    def export_schema(self, export_folder: str, file_name: str = 'outputSchema.json'):
        def _add_object_to_schema(out_schmea: dict, schema_obj: SchemaObject):
            for p in schema_obj.properties:
                out_schmea[p.name] = {'type': [_schema_type_to_string(p.type), 'null']}

                if p.default_value:
                    #  TODO: make sure to alert the user.
                    if p.type == SchemaObjectType.NUMBER or p.type == SchemaObjectType.INTEGER:
                        out_schmea[p.name]['default'] = int(p.default_value)
                    elif p.type == SchemaObjectType.BOOLEAN:
                        out_schmea[p.name]['default'] = False if p.default_value == 'False' else True
                    else:
                        out_schmea[p.name]['default'] = p.default_value
                
                if p.type == SchemaObjectType.ARRAY:
                    out_schmea[p.name]['items'] = {'type': [_schema_type_to_string(p.properties[0].type), 'null']}
                    if p.properties[0].type == SchemaObjectType.OBJECT:
                        out_schmea[p.name]['items']['properties'] = {}
                        _add_object_to_schema(out_schmea[p.name]['items']['properties'], p.properties[0])
                elif p.type == SchemaObjectType.OBJECT:
                    out_schmea[p.name]['properties'] = {}
                    _add_object_to_schema(out_schmea[p.name]['properties'], p)
        
        properties_schema = {}
        _add_object_to_schema(properties_schema, self)
        
        # Replacing tags, removing type and fitting into the accepted format
        properties_schema.pop('type', None)
        if 'tags' in properties_schema:
            properties_schema['tags'] = {'type': ['array', 'null'],
                    'items': {'type': ['object', 'null'],
                              'properties': {'Key': {'type': ['string', 'null']}, 'Value': {'type': ['string', 'null']} }}}
        
        out_schmea = {'$schema': 'http://json-schema.org/draft-04/schema#',
                      '$id': 'http://api.dome9.com/AzureEntityName.json',
                      'type': ['object', 'null'],
                      'properties': properties_schema}

        filename = os.path.join(export_folder, file_name) 
        with open(filename, 'w') as f:
            json.dump(out_schmea, f, indent=2)

        logging.info(f"exported schema to {filename}")

    @staticmethod
    def load_from_url(url: str, title_id: str, enrichment_url: str = '', enrichment_title_id: str = '', export_folder: str = '') -> None:

        logging.info(f"Creating schema from {url} with the id '{title_id}'")
        logging.info(f"'And enrichment from {enrichment_url} and id '{enrichment_title_id}'")

        # Grab HTML via selenuim (this could be replaced with just donwloading the source)
        # Didn't use request here because of the css added in this method that makes this parsing easier
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            browser = webdriver.Chrome(options=options)
            browser.get(url)
            main_html = browser.page_source
            if enrichment_url and enrichment_title_id:
                browser.get(enrichment_url)
                enrichment_html = browser.page_source
            browser.quit()
        except Exception as e:
            logging.critical(f"Couldn't get source pages from {url}{' or' + enrichment_url if enrichment_url else ''}")
            return

        try:
            main_soup = BeautifulSoup(main_html, 'html.parser')
        except Exception as e:
            logging.critical(f"Couldn't parse the html that were in {url}")
            logging.critical(e)
        try:
            if enrichment_url and enrichment_title_id:
                enrichment_soup = BeautifulSoup(enrichment_html, 'html.parser')
        except Exception as e:
            logging.critical(f"Couldn't parse the html that were in {enrichment_url}")
            logging.critical(e)
        
        try:
            schema_obj = SchemaObject.load_from_page(main_soup, title_id)
        except Exception as e:
            logging.critical(f"Couldn't load objects from {url}")
            logging.critical(e)
        
        try:
            if enrichment_url and enrichment_title_id:
                enrichment_obj = SchemaObject.load_from_page(enrichment_soup, enrichment_title_id)
                schema_obj.properties.append(enrichment_obj)
        except Exception as e:
            logging.critical(f"Couldn't load objects from {enrichment_url}")
            logging.critical(e)
        

        schema_obj.export_schema(export_folder)


    @staticmethod
    def load_from_page(soup: BeautifulSoup, title_id: str, parent_link_path: List[str] = None) -> 'SchemaObject':
        title_obj = soup.find("h3", {"id": title_id})
        if not title_obj:
            logging.critical(f"couldn't find id: '{title_id}', replacing with an empty object with '{title_id}' as the name")
            return SchemaObject(title_id, SchemaObjectType.OBJECT, [])
        title = title_obj.text.strip()
        
        table = soup.find(lambda tag: tag.name == "table" and "aria-label" in tag.attrs and tag.attrs["aria-label"] == title)
        if not table:
            table = title_obj.find_next('table')
        if not table:
            logging.critical(f"couldn't find table for: '{title}' (id: '{title_id}'), replacing with an empty object with '{title}' as the name")
            return SchemaObject(title, SchemaObjectType.OBJECT, [])
    
        rows = table.find_all('tr')        
        if not rows:
            logging.critical(f"couldn't find rows for: '{title}' (id: '{title_id}'), replacing with an empty object with '{title}' as the name")
            return SchemaObject(title, SchemaObjectType.OBJECT, []) 

        if parent_link_path:
            my_link_path = parent_link_path.copy()
        else:
            my_link_path = []
        my_link_path.append(title_id)
        schema_obj = SchemaObject(title, SchemaObjectType.OBJECT, [], my_link_path)

        for row in rows[1:]:
            cols = row.find_all('td')
            if not cols or len(cols) < 2:
                continue
            
            default_value = ''
            if len(cols) == 3:
                name, type_, desc = [el.text.strip() for el in cols]
            if len(cols) == 4:
                name, type_, default_value, desc = [el.text.strip() for el in cols]
            
            link = cols[1].find('a')
            link = link['href'][1:] if link else ''         

            clean_name = name.split('.')[-1]
            path = name.split('.')[:-1]

            new_schema_obj = _create_schema_object_recursive(soup, clean_name, type_, default_value, desc, link, my_link_path)
            _add_obj_schemaobject_path(schema_obj, new_schema_obj, path, my_link_path)

        return schema_obj
