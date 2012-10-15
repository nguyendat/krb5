'''
  Copyright 2011 by the Massachusetts
  Institute of Technology.  All Rights Reserved.

  Export of this software from the United States of America may
  require a specific license from the United States Government.
  It is the responsibility of any person or organization contemplating
  export to obtain such a license before exporting.

  WITHIN THAT CONSTRAINT, permission to use, copy, modify, and
  distribute this software and its documentation for any purpose and
  without fee is hereby granted, provided that the above copyright
  notice appear in all copies and that both that copyright notice and
  this permission notice appear in supporting documentation, and that
  the name of M.I.T. not be used in advertising or publicity pertaining
  to distribution of the software without specific, written prior
  permission.  Furthermore if you modify this software you must label
  your software as modified software and not distribute it in such a
  fashion that it might be confused with the original M.I.T. software.
  M.I.T. makes no representations about the suitability of
  this software for any purpose.  It is provided "as is" without express
  or implied warranty.
'''

import sys
import os
import re

from lxml import etree

from docmodel import *


class DoxyTypes(object):
    def __init__(self, xmlpath):
        self.xmlpath = xmlpath

    def run_compound(self, filename, include=None):
        path = '%s/%s' % (self.xmlpath,filename)
        tree = etree.parse(path)
        root = tree.getroot()

        brief_node = root.xpath('./compounddef/briefdescription')[0]
        brief_description = self._get_brief_description(brief_node)
        details_node = root.xpath('./compounddef/detaileddescription')[0]
        detailed_description = self._get_detailed_description(details_node)

        fields = list()
        for node in root.iterfind(".//memberdef[@kind]"):
            data = {}
            kind = node.attrib['kind']
            if include is None or kind in include:
                if kind == 'variable':
                    data = self._process_variable_node(node)
                else:
                    pass
                fields.append(data)

        result = {'brief_description': brief_description,
                  'detailed_description': detailed_description,
                  'attributes': fields}

        return result



    def run(self, filename, include=None):
        """
        Parses xml file generated by doxygen.

        @param filename: doxygen xml file name
        @param include: members sections to include, in None -- include all
        """
        path = '%s/%s' % (self.xmlpath,filename)
        tree = etree.parse(path)
        root = tree.getroot()
        result = list()
        for node in root.iterfind(".//memberdef[@kind]"):
            data = {}
            kind = node.attrib['kind']
            if include is None or kind in include:
                if kind == 'typedef':
                    data = self._process_typedef_node(node)
                elif kind == 'variable':
                    data = self._process_variable_node(node)
                elif kind == 'define':
                    data = self._process_define_node(node)
                result.append(data)
        print "\nnumber of types processed ==> " , len(result)
        return result


    def _process_typedef_node(self, node):
        t_name = node.xpath('./name/text()')[0]

        print  t_name

        t_Id = node.attrib['id']
        t_definition = node.xpath('./definition/text()')[0]
        t_type = self._process_type_node(node.xpath("./type")[0])
        brief_node = node.xpath('./briefdescription')[0]
        t_brief = self._get_brief_description(brief_node)
        details_node = node.xpath('./detaileddescription')[0]
        t_detailed = self._get_detailed_description(details_node)
        # remove  macros
        t_definition = re.sub('KRB5_CALLCONV_C', '', t_definition)
        t_definition = re.sub('KRB5_CALLCONV', '', t_definition)
        t_definition = re.sub('\*', '\\*', t_definition)
        # handle fp
        if t_type[1].find('(') >= 0:
              t_type = (t_type[0],None)

        typedef_descr = {'category': 'composite',
                         'definition': t_definition,
                         'name': t_name,
                         'Id': t_Id,
                         'initializer': '',
                         'type': t_type[1],
                         'short_description': t_brief,
                         'long_description': t_detailed,
                         'attributes': list()
                          }
        if t_type[0] is not None :
            filename = '%s.xml' % t_type[0]
            path = '%s/%s' % (self.xmlpath,filename)
            if not os.path.exists(path):
                # nothing can be done
                return typedef_descr

            compound_info = self.run_compound(filename)
            if compound_info is not None:
                brief_description =  compound_info.get('brief_description')
                if brief_description is not None and len(brief_description):
                    # override brief description
                    typedef_descr['short_description'] = brief_description
                detailed_description = compound_info.get('detailed_description')
                if detailed_description is not None and len(detailed_description):
                    # check if this is not a duplicate
                    if detailed_description.find(t_detailed) < 0:
                        typedef_descr['long_description'] = '%s\n%s' % \
                            (detailed_description,
                             typedef_descr['long_description'])
                typedef_descr['attributes'] = compound_info['attributes']
        return typedef_descr

    def _process_variable_node(self, node):
        v_name = node.xpath('./name/text()')[0]
        v_Id = node.attrib['id']
        v_definition = node.xpath('./definition/text()')[0]
        v_type = self._process_type_node(node.xpath("./type")[0])
        brief_node = node.xpath('./briefdescription')[0]
        v_brief = self._get_brief_description(brief_node)
        details_node = node.xpath('./detaileddescription')[0]
        detailed_description = self._get_detailed_description(details_node)
        # remove  macros
        v_definition = re.sub('KRB5_CALLCONV_C', '', v_definition)
        v_definition = re.sub('KRB5_CALLCONV', '', v_definition)
        v_definition = re.sub('\*', '\\*', v_definition)

        variable_descr = {'category': 'variable',
                          'definition': v_definition,
                          'name': v_name,
                          'Id': v_Id,
                          'initializer': '',
                          'type': v_type[1],
                          'short_description': v_brief,
                          'long_description': detailed_description,
                          'attributes': list()
                          }

        return variable_descr

    def _process_define_node(self, node):
        d_name = node.xpath('./name/text()')[0]
        print  d_name
        d_initializer = ''
        d_type = ''
        d_signature = ''

        # Process param/defname node
        if len(node.xpath('./param/defname')) > 0:
            prm_str = ''
            prm_list = list()
            for p in node.xpath("./param"):
                x = self._process_paragraph_content(p)
                if x is not None and len(x):
                   prm_list.append(x)
            if prm_list is not None:
                prm_str = prm_str.join(prm_list)
            d_signature = " %s (%s) " % (d_name , prm_str)
            d_signature = re.sub(', \)', ')', d_signature)

        if len(node.xpath('./initializer')) > 0:
            len_ref = len(node.xpath('./initializer/ref'))
            if len(node.xpath('./initializer/ref')) > 0:
                d_type = self._process_type_node(node.xpath("./initializer/ref")[0])
            if len(d_type) > 0:
                len_text = len(node.xpath('./initializer/text()'))
                if len_text == 0 and d_type[1]:
                    d_initializer = d_type[1]
                if len_text > 0 and len(node.xpath('./initializer/text()')[0]) > 0:
                    d_initializer = node.xpath('./initializer/text()')[0] + d_type[1]
                if len_text > 1:
                    if node.xpath('./initializer/text()')[1] is not None:
                        d_initializer = d_initializer + node.xpath('./initializer/text()')[1]
            else:
                d_initializer = node.xpath('./initializer/text()')[0]
        d_Id = node.attrib['id']
        brief_node = node.xpath('./briefdescription')[0]
        d_brief = self._get_brief_description(brief_node)
        details_node = node.xpath('./detaileddescription')[0]
        detailed_description = self._get_detailed_description(details_node)

        define_descr = {'category': 'composite',
                        'definition': '',
                        'name': d_name,
                        'name_signature': d_signature,
                        'Id': d_Id,
                        'initializer': d_initializer,
                        'type': '',
                        'short_description': d_brief,
                        'long_description': detailed_description,
                        'attributes': list()
                        }

        return define_descr


    def _get_brief_description(self, node):
        result = list()
        for p in node.xpath("./para"):
                x = self._process_paragraph_content(p)
                if x is not None and len(x):
                    result.append(x)
        result = '\n'.join(result)

        return result


    def _get_detailed_description(self, node):
        """
        Description node is comprised of <para>...</para> sections.
        There are few types of these sections:
           a) Content section
           b) Return value section -- skip
           c) Parameter list section -- skip
        @param node: detailed description node
        """
        result = list()
        for p in node.xpath("./para"):
            if len(p.xpath("./simplesect[@kind='return']")):
                continue
            elif len(p.xpath("./parameterlist[@kind='param']")):
                continue
            else:
                x = self._process_paragraph_content(p)
                result.append(x)
        result = '\n'.join(result)

        return result

    def _process_paragraph_content(self, node):

        result = list()
        content = node.xpath(".//text()")
        for e in content:
            if node is e.getparent():
                result.append(e.strip())
            elif e.getparent().tag == 'ref':
                if e.is_tail:
                    result.append(e.strip())
                else:
                    result.append(':c:type:`%s`' % e.strip())
            elif e.getparent().tag == 'emphasis':
                if e.is_tail:
                    result.append(e.strip())
                else:
                    result.append('*%s*' % e.strip())
            elif e.getparent().tag == 'computeroutput':
                if e.is_tail:
                    result.append(e.strip())
                else:
                    result.append('*%s*' % e.strip())
            elif  e.getparent().tag == 'defname':
                result.append('%s, ' % e.strip())
        result = ' '.join(result)

        return result

    def _process_type_node(self, node):
        """
        Type node has form
            <type>type_string</type>
        for build in types and
            <type>
              <ref refid='reference',kindref='member|compound'>
                  'type_name'
              </ref></type>
              postfix (ex. *, **m, etc.)
            </type>
        for user defined types.
        """
        p_id = node.xpath("./ref/@refid")
        if len(p_id) == 1:
            p_id = p_id[0]
        elif len(p_id) == 0:
            p_id = None
        p_type = ' '.join(node.xpath(".//text()"))

        # remove  macros
        p_type = re.sub('KRB5_CALLCONV_C', ' ', p_type)
        p_type = re.sub('KRB5_CALLCONV', ' ', p_type)

        return (p_id,p_type)

    def save(self, obj, templates, target_dir):
        template_path = templates[obj.category]
        outpath = '%s/%s.rst' % (target_dir,obj.name)
        obj.save(outpath, template_path)



class DoxyTypesTest(DoxyTypes):
    def __init__(self, xmlpath, rstpath):
        self.templates = { 'composite': 'type_document.tmpl'}
        self.target_dir = rstpath

        super(DoxyTypesTest,self).__init__(xmlpath)

    def run_tests(self):
        print "Process typedef's"
        self.test_process_typedef_node()
        print "Process define's"
        self.test_process_define_node()

    def test_run(self):
        filename = 'krb5_8hin.xml'
        self.run(filename)

    def test_process_variable_node(self):
        filename = 'struct__krb5__octet__data.xml'
        result = self.run(filename, include=['variable'])

    def test_process_typedef_node(self):
        # run parser for typedefs
        filename = 'krb5_8hin.xml'
        result = self.run(filename, include=['typedef'])
        target_dir = '%s/types' % (self.target_dir)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, 0755)
        for t in result:
            obj = DocModel(**t)
            self.save(obj, self.templates, target_dir)

    def test_process_define_node(self):
        # run parser for define's
        filename = 'krb5_8hin.xml'
        result = self.run(filename, include=['define'])
        target_dir = '%s/macros' % (self.target_dir)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, 0755)
        for t in result:
            obj = DocModel(**t)
            tmpl = {'composite': 'define_document.tmpl'}
            self.save(obj, tmpl, target_dir)

if __name__ == '__main__':

    tester = DoxyTypesTest( xml_inpath, rst_outpath)
    tester.run_tests()
