import frappe
from email.utils import formataddr
from frappe.utils import now
from frappe.utils import nowdate, add_days, getdate, get_time, add_months
import datetime
from datetime import  timedelta, date, time
from frappe.desk.reportview import get_filters_cond, get_match_cond
	
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def service_type_query(doctype, txt, searchfield, start, page_len, filters):
	conditions = []
	
	if txt:
		conditions="and building.service_type like '%{}%'".format(txt)
	else:
		conditions=''
	return frappe.db.sql("""select building.service_type 
	from `tabBuilding` as building 
	where building.building_name ='{building_name}' {conditions}
	 """.format(building_name=filters.get("building_name"),conditions=conditions
	))

def validate_mobile_no(self):
	if not self.contact_mobile.startswith("+971") and not self.contact_mobile.startswith("971"):
		frappe.throw("Client Phone Number Must start with 971 or +971")

@frappe.whitelist()
def get_building_detail(building_name,service_type):
	if building_name and service_type:
		data = frappe.db.sql("""
			SELECT name
			FROM `tabBuilding` as b
			where b.building_name = '%s' and b.service_type = '%s'
        	limit 1
		""" % (building_name,service_type),as_dict=1)
		if data:
			return data

@frappe.whitelist()
def get_escalation_matrix(building_name):
	escalation_detail = frappe.db.sql("""select parent from `tabEscalation Building Name` where building_name ='{}' """.format(building_name),as_dict=1)
	if escalation_detail:
		return escalation_detail[0]['parent']

def issue_validate(self,method):
	validate_mobile_no(self)
	calculate_due_date(self)
	#escalation_email(self)

def calculate_due_date(self):
	import datetime
	default_holiday = frappe.db.get_value("Company","ROAM",'default_holiday_list')
	holiday = frappe.get_doc("Holiday List",default_holiday)
	holiday_list =[row.holiday_date for row in holiday.holidays]

	due_date = getdate(self.opening_date)
	opening_time = get_time(self.opening_time)

	if due_date not in holiday_list:
		due_date = (datetime.datetime.combine(due_date, opening_time) + timedelta(hours=12))
	else:
		due_date = (datetime.datetime.combine(add_days(due_date,1), opening_time) + timedelta(hours=12))
	
	self.due_date = due_date

def escalation_email():
	from datetime import datetime, time
	issue_list=frappe.db.get_all("Issue",{"job_status_by_sp":'In progress'})
	print(issue_list)
	for each in issue_list:
		doc=frappe.get_doc("Issue",each.name)
		date_format_str = '%Y-%m-%d %H:%M:%S.%f'
		now = datetime.strptime(str(frappe.utils.now()), date_format_str)
		creation =   datetime.strptime(str(datetime.combine(datetime.strptime(str(doc.opening_date),'%Y-%m-%d'),datetime.strptime(str(doc.opening_time),'%H:%M:%S.%f').time())), date_format_str)
		diff = now - creation
		hours = int(abs(diff.total_seconds() / 3600))
		print(doc.name) 
		print(str(now))
		print(str(creation))
		print(str(diff))
		print(str(hours))
		receipient=send_email_receipients(doc.name,hours)
		print(receipient)
		if hours in [12,24,36]:
			if hours == 12 and not doc.level_1_email_sent:
				print("12")
				for email in receipient.keys():
					send_email(doc,email,receipient[email],hours)
					print("sent")
			if hours == 24 and not doc.level_2_email_sent:
				for email in receipient.keys():
					print("sent")
					send_email(doc,email,receipient[email],hours)
			if hours == 36 and not doc.level_3_email_sent:
				for email in receipient.keys():
					send_email(doc,email,receipient[email],hours)
					print("sent")


def send_email_receipients(name,hours):
	doc=frappe.get_doc("Issue",name)
	receipient={}
	print(receipient)
	if not hours > 36:
		if hours >= 12:
			receipient.update({doc.level_1_email:doc.level_1_contact_person})
			if not doc.level_1_email_sent:
				frappe.db.set_value("Issue",doc.name,"level_1_email_sent",1)
		if hours >= 24:
			receipient.update({doc.level_2_email:doc.level_2_contact_person})
			if not doc.level_2_email_sent:
				frappe.db.set_value("Issue",doc.name,"level_2_email_sent",1)
		if hours >= 36:
			receipient.update({doc.level_3_email:doc.level_3_contact_person})
			if not doc.level_3_email_sent:
				frappe.db.set_value("Issue",doc.name,"level_3_email_sent",1)
		print(receipient)
		# doc.save()
	if doc.reliance_team_email:
		if doc.reliance_team_email not in receipient.keys():
			receipient[doc.reliance_team_email]=""
	if doc.sp_email_addresses:
		if doc.sp_email_addresses not in receipient.keys():
			receipient[doc.sp_email_addresses]=""
	return receipient
	


def send_email(doc,email,name,hours):
	subject = "Escalation. Case Number {} ".format(doc.name)
	email_template = frappe.get_doc("Email Template", "Escalation Email")
	args={"doc":doc,"hours":hours,"receiver_name":name}
	content = frappe.render_template(email_template.response_html, args)
	# for multiple email id
	print(email)
	print("sending")
	if email:
		email = email.split(',')
		frappe.sendmail(
		recipients=email,
		cc = '',
		subject = subject ,
		message = content,
		now = 1
	)

# datetime.combine(datetime.strptime('2021-10-27','%Y-%m-%d'),datetime.strptime('8:53:29.362656','%H:%M:%S.%f').time())

# date_format_str = '%H:%M:%S.%f'
# now =   datetime.strptime(str(datetime.now()), date_format_str)
# creation =   datetime.strptime("2021-07-24 11:13:08.230010", date_format_str)
# diff = now - creation 
# diff_in_hours = int(abs(diff.total_seconds() / 3600))

# datetime.strptime(str("16:50:46"), date_format_str) +timedelta(hours=12)