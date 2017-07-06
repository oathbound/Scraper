from twill.commands import get_browser, go, redirect_output, formclear, fv, showforms, submit, formaction, code, save_html, showlinks
from bs4 import BeautifulSoup
from time import sleep
from io import BytesIO
from PIL import Image
import base64
import cStringIO
from shutil import copy, copyfile
from random import randint
import codecs

import os

#from weasyprint import HTML, CSS

class CXScraper:
    def __init__(self, domain, un, pw, path_for_files=""):
        """
        domain must start with protocol (http/s, ftp, etc) and end with slash
        """
        self.domain = domain.strip()
        if self.domain[-1] !='/':
            self.domain =  self.domain + '/'
                
        self.un = un.strip()
        self.passw = pw.strip()
        self.path_for_files = path_for_files

        self.valid_cust_ids=[]
        self.valid_acct_ids=[]

        self.page=""
        self.browser=None

        
    
    def login(self, un="", passw=""):
        """
        To Add:  check login worked somehow.
        """
        go(self.domain)
        self.b = get_browser()

        use_un = self.un
        use_pw = self.passw
        if (un != "" and passw != ""):
            use_un = un
            use_pw = passw
        
        fv("2", "username", self.un)
        fv("2", "password", self.passw)
        f=self.b.get_form("2")
        formaction("2", self.domain+f.action)
        self.b.submit()

    def getCustDetailsPage(self, cust_id):
        c_id = int(cust_id)

        url = "%s%s%d" % (self.domain,"customers/view/",c_id)
        go(url)
        b = get_browser()
        
        self.page= b.get_html()

    def getCustomerDocsPage(self, cust_id):
        """
        Loads the customer docs page for the given customer
        """
        c_id = int(cust_id)

        url = "%s%s%d" % (self.domain,"customerDocuments/ls/",c_id)
        go(url)
        b = get_browser()
        
        self.page= b.get_html()
        self.browser=b

        
    def getCustomerDocList(self, cust_id):
        """
        extracts a list of docs from the customer docs page.
        returns a list of doc ids.
        """
        self.getCustomerDocsPage(cust_id)
        doclinks = []
        for (label, url) in self.browser.get_all_links():
            if label == "View":
                safe_url = url.lstrip('/')
                someid = int(safe_url[safe_url.rfind('/')+1:])
                doclinks.append(someid)
        
        #print doclinks
        return doclinks

    def loadPage(self, some_string, some_id):
        url = "%s%s%d" % (self.domain,some_string.lstrip('/'), some_id)
        #print url
        go(url)

        self.browser=get_browser()
        self.page= self.browser.get_html()
        

    def getCustomerDoc(self, cust_id, doc_id):
        """
        Loads the requested doc.
        DLs the doc file to path_for_files
        Returns a dict with the info about the doc.
        """
        self.loadPage("customerDocuments/view/", doc_id)

        doc_data = {}
        soup = BeautifulSoup(self.page, 'lxml')
        #parse the data here....
        
        table = soup.find('dl')
        row = table.find('dt')
        last_key = ""
        while(1):
            if row.name == u'dt':
                last_key = row.contents[0].strip()
                doc_data[last_key.strip()] = ""
            elif row.name == u'dd':
                doc_data[last_key] = u''.join(row.contents[0].strip())
                print last_key, " => ", doc_data[last_key]
            else:
                print row
                if row is None:
                    break
                row = row.next_sibling
                continue
            #print row.next_sibling.next_sibling
            row = row.next_sibling.next_sibling
            if row is None:
                break

        ##
        #Copy in the customer file from the bulk DL.
        ##  This needs better error handling!!!!!
        if doc_data['Filename']=="":
            doc_data['Filename'] = "---"
        else:
            src = "C:\\Users\\Alex\\Desktop\\basisdocs\\customerDocuments\\%s"%doc_data['Filename']
            dest = "%s%d/%s"%(self.path_for_files, cust_id, doc_data['Filename'])
            print dest
            try:
                if os.stat(dest):
                    print "File already exists"
                else:
                    copy(src, dest)
            except:
                copy(src, dest)
        
        return doc_data

    def getCustomerDocs(self, cust_id):
        """
        DLs all the Customer's docs to path_for_files
        Creates a txt file w info for all docs)
        """
        #get the list of docs for the customers- just a list of ids.
        #load each id (doc)
        docs = self.getCustomerDocList(cust_id)
        if docs == []:
            self.writeDocsToFile(cust_id, "")
        else:
            dir_for_files = "%s%d"%(self.path_for_files, cust_id)
            try:
                os.stat(dir_for_files)
            except:
                os.mkdir(dir_for_files)
            
            doc_info = {}
            for doc_id in docs:
                doc_info[doc_id]= self.getCustomerDoc(cust_id, doc_id)

            self.writeDocsToFile(cust_id, doc_info)

        
    def writeDocsToFile(self, cust_id, doc_info=""):
        dir_for_files = "%s%d"%(self.path_for_files, cust_id)

        try:
            os.stat(dir_for_files)
        except:
            os.mkdir(dir_for_files)
        
        doc = codecs.open("%s%s"%(dir_for_files, "/doc_info.txt"), 'w', encoding="utf-8")
        
        if doc_info == "":
            doc.write("There were no documents in CX for this customer id.")
        else:
            for d in doc_info.keys():
                if doc_info[d] is None:
                    doc.write("ERROR:  No data found for this file.\n")
                    continue
                for k in doc_info[d]:
                   writestr = u"%s:%s\n"%(unicode(k), unicode(doc_info[d][k]))
                   doc.write(unicode(writestr))
                doc.write("-------\n\n")
        doc.close()
            
               
        

    def customerExists(self, cust_id):
        """
        Looks up if a customer exists.
        """
        if cust_id in self.valid_cust_ids:
            return True
        elif self.customerPageExists(cust_id):
            self.valid_cust_ids.append(cust_id)
            return True
        else:
            return False

    def customerPageExists(self, cust_id):
        url = "%s%s%d" % (self.domain,"customers/view/",cust_id)
        print url
        go(url)
        b = get_browser()
        soup = BeautifulSoup(b.get_html(),'lxml')
        flash = soup.find('div', attrs={'id':'flashMessage', 'class':'message'})

        if flash is None:
            return True
        if flash.contents[0]==u'Invalid Customer' or flash.contents[0]=="Invalid Customer":
            return False
        else:
            #Wtf?  Return false I guess.
            return False

    def ParseDLData(self, table):
        """
        table -  is a beautiful soup object that holds a a dl table.
            the table is such that each dt is a key which may have data in a following dd.

        Returns a dict where the dt items are keys, and the dd items (if existing) are values.
        """
        table_data={}
        row = table.find('dt')
        last_key = ""
        while(1):
            if row.name == u'dt':
                last_key = row.text.strip()
                table_data[last_key] = ""
            elif row.name == u'dd':
                table_data[last_key] = u''.join(row.text.strip()) 
                print last_key, " => ", table_data[last_key]
            else:
                print 'wtf=',row
                if row is None:
                    break
                row = row.next_sibling
                continue
            #print row.next_sibling.next_sibling
            row = row.next_sibling.next_sibling
            if row is None:
                break
        return table_data

    def ParseFieldBagTable(Self, table):
        """
        table -  is a beautiful soup object that holds a a dl table.
            the table is such that each dt is a key which may have data in a following dd.
            The table may contain sections headers (h2) and subsection headers (h3).

        Returns a dict where the section headers (h2) are keys to dicts in which
            subsection headers (h3) and dt items are keys.
            subsections headers reference to dics keyed by dt data.
            dt keys have dd values or ""
            dt items are keys, and the dd items (if existing) are values.
        """
        table_data={}
        row = table.find('h2')
        last_h2 = ""
        last_h3 = ""
        last_dt = ""
        while(1):
            if row.name == u'h2':
                last_h2 = row.text.strip()
                last_h3="" #clear the last_h3. no h2 are within h3.
                table_data[last_h2] = {}
                print last_h2
            elif row.name == u'h3':
                #all h3 are within an h2
                last_h3 = row.text.strip()
                table_data[last_h2][last_h3] = {}
                print '\t',last_h3
            elif row.name == u'dt':
                #dts can be inside an h2 or an h3.  how do we know?
                last_dt = row.text.strip()
                if(last_h3 == ""):
                    table_data[last_h2][last_dt] = ""
                else : #this dt belongs to an h2
                    table_data[last_h2][last_h3][last_dt] = ""                    
            elif row.name == u'dd':
                if(last_h3==""):
                    table_data[last_h2][last_dt] = u''.join(row.text.strip())
                    print '\t', last_dt, " => ", table_data[last_h2][last_dt]
                else:
                    table_data[last_h2][last_h3][last_dt] = u''.join(row.text.strip())
                    print '\t\t', last_dt, " => ", table_data[last_h2][last_h3][last_dt]
            else:
                print 'wtf=',row
                if row is None:
                    break
                row = row.next_sibling
                continue
            #print row.next_sibling.next_sibling
            row = row.next_sibling.next_sibling
            if row is None:
                break
        return table_data

    def ParseScaffoldTable(self, table):
        """
        table -  is a beautiful soup object that holds a table of class "scaffold list"
                the table contains 'tbody'
                the first tr contains 'th'
                th are column names.
                td is the data for other rows

        Returns a list of the table data rows, where the first row is list of the column headings,
            and every row there after is a list
        """
        table_data=[]
        this_row=[]
        #tbody = table.find('tbody', recursive="False")

        for tr in table.find_all('tr', recursive="False"):
            for td in tr.find_all('td', recursive="False"):
                this_row.append(u''.join(td.text.strip()))
            if(this_row != []):
                table_data.append(this_row)
            print this_row
            this_row=[]          

        print table_data
        return table_data
            
        
    def getScaffoldTableInfo(self, div_attributes):
        """
        div_attributes is a dict of the id and or class data by which to find the scaffold table to parse.
        """
        soup = BeautifulSoup(self.page, 'lxml')
        div = soup.find('div', div_attributes)
        table = div.find('table')
        if table is None:
            return []
        return self.ParseScaffoldTable(div)


    def ParseCustomerBasicInfo(self, cust_id):
        soup = BeautifulSoup(self.page, 'lxml')
        table = soup.find('dl')
        #print table
        return  self.ParseDLData(table)
        
    def ParseCustomerAppInfo(self, cust_id):
        soup = BeautifulSoup(self.page, 'lxml')
        table = soup.find('dl', {'class':"dlFieldBag"})
        #print table
        return self.ParseFieldBagTable(table)


    def ParseAccountBasicInfo(self):
        soup = BeautifulSoup(self.page, 'lxml')
        table = soup.find('dl')
        #print table
        return  self.ParseDLData(table)

    def getCustomerAccountIDs(self, acct_list):
        """
        Account list is a list,
        each item is a tuple
        the id is the 0 element in each tuple
        """
        print acct_list
        return [acct[0] for acct in acct_list]

    

    def getAccountInfo(self, acct_id):
        print "Called for acct id ", acct_id

        acct_info_dict = {}
        self.loadPage("accounts/view/", int(acct_id))

        acct_info_dict['Basic']=self.ParseAccountBasicInfo()
        acct_info_dict['Status History']=self.getScaffoldTableInfo({'id':'StatusHistorySection','class':'StatusHistory'})
        acct_info_dict['Deposits']=self.getScaffoldTableInfo({'id':'MoneySection','class':'Deposits'})
        acct_info_dict['Withdrawals']=self.getScaffoldTableInfo({'class':'Withdrawals'})
        acct_info_dict['Payments']=self.getScaffoldTableInfo({'class':'Payments'})
        acct_info_dict['Bonuses']=self.getScaffoldTableInfo({'class':'TradeBonuses'})
        acct_info_dict['Audit Trail']=self.getScaffoldTableInfo({'id':'AuditTrail'})
        acct_info_dict['Admin Notes']=self.getScaffoldTableInfo({'id':'AdminNotesHistory'})
                
        return acct_info_dict

    def getCustomerInfo(self, cust_id):
        custInfoDict = {}
        self.loadPage("customers/view/", cust_id)
        custInfoDict['Basic'] = self.ParseCustomerBasicInfo(cust_id)
        custInfoDict['App'] = self.ParseCustomerAppInfo(cust_id)

        custInfoDict['Status History'] = self.getScaffoldTableInfo({'id':'StatusHistory'})
        custInfoDict['Accounts'] = self.getScaffoldTableInfo({'id':'Accounts'})
        custInfoDict['Requests'] = self.getScaffoldTableInfo({'id':'Requests'})
        custInfoDict['Bonuses'] = self.getScaffoldTableInfo({'id':'BonusesSection'})
        custInfoDict['EMail Log'] = self.getScaffoldTableInfo({'id':'EmailLog'})
        custInfoDict['Audit Trail'] = self.getScaffoldTableInfo({'id':'AuditTrail'})
        custInfoDict['AdminNotes'] = self.getScaffoldTableInfo({'id':'AdminNotesHistory'})
        
        """
        #VPS pending...no one uses it.
        custInfoDict['VPS History']= self.ParseCustomerVPSHistory(cust_id) 
        """

        """
        look at account data, get all the accounts by their ID.
        """
        custAccounts = []
        for acct_id in self.getCustomerAccountIDs(custInfoDict['Accounts']):
            custAccounts.append(self.getAccountInfo(acct_id))
            

            

def getAllCustomerDocs(cxScraper):
    """
    Gets all Docs for all Customers
    """
    for i in range(151,1000):
        if cxs.customerExists(i):
            print "Getting Customer Docs for %d"%(i)
            cxs.getCustomerDocs(i)
            print "Got docs for Customer %d"%(i)
            sleep(randint(1,5)) #sleep for a second

def getAllCustomerData(cxScraper):
    """
    Gets all the customer info.
    Puts it in a file in a dir w cust id.
    """
    for i in range(60,61):
        if cxs.customerExists(i):
            print "Getting Customer Info for %d"%(i)
            cxs.getCustomerInfo(i)
            print "Got docs for Customer %d"%(i)
            sleep(randint(1,5)) #sleep for a second or 5
            


if __name__=="__main__":
    admindomain = ''
    thisun=""
    thispassw = ""
    
    #cxs = CXScraper(admindomain, thisun, thispassw, "C:\\Users\\Alex\\Dropbox (GCM Prime Ltd)\\cx scraper copier\\BASIS CUST DOCS\\")

    cxs.login()
    cxs.getCustDetailsPage(60)
    #print cxs.customerPageExists(60)
    #print cxs.customerPageExists(4444)
    #cxs.getCustomerDocs(9)
    getAllCustomerData(cxs)

    
#######################
# KNOWN BUGS:
#   1- check doc actually appeared
#   2- if there are more than 20 docs,
#        doclist does not follow paging links to the nth page
#
#
        
