from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

@tagged('post_install', '-at_install', 'payroll_reports')
class TestHrPayrollReports(TransactionCase):
    """Test cases for Colombian payroll reports in Odoo v18."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test company
        cls.company = cls.env['res.company'].create({
            'name': 'Test Company CO',
            'country_id': cls.env.ref('base.co').id,
        })
        
        # Set current user's company
        cls.env.user.company_id = cls.company
        
        # Create employee category
        cls.category_a = cls.env['hr.employee.category'].create({
            'name': 'Categoria A'
        })
        
        # Create department
        cls.department = cls.env['hr.department'].create({
            'name': 'Departamento de Prueba',
            'company_id': cls.company.id,
        })
        
        # Create job position
        cls.job = cls.env['hr.job'].create({
            'name': 'Desarrollador',
            'company_id': cls.company.id,
            'department_id': cls.department.id,
        })
        
        # Create employee
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Empleado de Prueba',
            'identification_id': '1234567890',
            'gender': 'male',
            'birthday': '1990-01-01',
            'country_id': cls.env.ref('base.co').id,
            'department_id': cls.department.id,
            'job_id': cls.job.id,
            'category_ids': [(4, cls.category_a.id)],
            'company_id': cls.company.id,
        })
        
        # Create contract type
        cls.contract_type = cls.env['hr.contract.type'].create({
            'name': 'Contrato Indefinido',
            'colombia_type': 'indefinite',
        })
        
        # Create payroll structure type (new in v18)
        cls.structure_type = cls.env['hr.payroll.structure.type'].search(
            [('country_id', '=', cls.env.ref('base.co').id)], limit=1)
        if not cls.structure_type:
            cls.structure_type = cls.env['hr.payroll.structure.type'].create({
                'name': 'Estructura Colombia',
                'country_id': cls.env.ref('base.co').id,
            })
        
        # Get Colombian payroll structure
        cls.structure = cls.env['hr.payroll.structure'].search(
            [('country_id', '=', cls.env.ref('base.co').id)], limit=1)
        
        # Create contract
        cls.contract = cls.env['hr.contract'].create({
            'name': 'Contrato de Prueba',
            'employee_id': cls.employee.id,
            'job_id': cls.job.id,
            'type_id': cls.contract_type.id,
            'wage': 1500000.0,  # SMLV 2023
            'state': 'open',  # v18 uses 'open' instead of 'running'
            'date_start': date.today() - relativedelta(months=6),
            'structure_type_id': cls.structure_type.id,  # New in v18
            'resource_calendar_id': cls.env.ref('resource.resource_calendar_std').id,
            'company_id': cls.company.id,
        })
        
        # Create payslip
        cls.payslip = cls.env['hr.payslip'].create({
            'name': 'Nómina de Prueba',
            'employee_id': cls.employee.id,
            'contract_id': cls.contract.id,
            'struct_id': cls.structure.id,
            'date_from': date.today().replace(day=1),
            'date_to': date.today().replace(day=28),
            'company_id': cls.company.id,
        })
        
        # Compute payslip
        cls.payslip.compute_sheet()
        cls.payslip.action_payslip_done()

    def test_income_certificate_report(self):
        """Test the generation of income certificate report."""
        # Create wizard for income certificate
        wizard = self.env['hr.payroll.income.certificate.wizard'].create({
            'employee_id': self.employee.id,
            'year': date.today().year,
            'company_id': self.company.id,
        })
        
        # Generate report
        result = wizard.generate_report()
        
        # Check if report was generated
        self.assertTrue(result, "Income certificate report was not generated")
        self.assertEqual(result.get('type'), 'ir.actions.report', 
                         "Action returned is not a report")

    def test_severance_payment_report(self):
        """Test the generation of severance payment report."""
        # Create wizard for severance payment
        wizard = self.env['hr.payroll.severance.payment.wizard'].create({
            'employee_id': self.employee.id,
            'year': date.today().year,
            'company_id': self.company.id,
        })
        
        # Generate report
        result = wizard.generate_report()
        
        # Check if report was generated
        self.assertTrue(result, "Severance payment report was not generated")
        self.assertEqual(result.get('type'), 'ir.actions.report', 
                         "Action returned is not a report")

    def test_payslip_report(self):
        """Test the generation of payslip report."""
        # Generate payslip report
        report_action = self.payslip.action_print_payslip()
        
        # Check if report was generated
        self.assertTrue(report_action, "Payslip report was not generated")
        self.assertEqual(report_action.get('type'), 'ir.actions.report', 
                         "Action returned is not a report")
        
    def test_payslip_batch_report(self):
        """Test the generation of payslip batch report."""
        # Create payslip batch
        batch = self.env['hr.payslip.run'].create({
            'name': 'Lote de Nómina de Prueba',
            'date_start': date.today().replace(day=1),
            'date_end': date.today().replace(day=28),
            'company_id': self.company.id,
        })
        
        # Add payslip to batch
        self.payslip.payslip_run_id = batch.id
        
        # Generate batch report
        report_action = batch.action_print_payslip_batch()
        
        # Check if report was generated
        self.assertTrue(report_action, "Payslip batch report was not generated")
        self.assertEqual(report_action.get('type'), 'ir.actions.report', 
                         "Action returned is not a report")

    def test_electronic_payroll_report(self):
        """Test the generation of electronic payroll report for DIAN."""
        # Create electronic payroll document
        electronic_payroll = self.env['hr.electronic.payroll'].create({
            'name': 'Nómina Electrónica de Prueba',
            'company_id': self.company.id,
            'date_start': date.today().replace(day=1),
            'date_end': date.today().replace(day=28),
        })
        
        # Add payslip to electronic payroll
        electronic_payroll.write({
            'payslip_ids': [(4, self.payslip.id)]
        })
        
        # Generate electronic payroll report
        electronic_payroll.generate_electronic_payroll()
        
        # Check if electronic payroll was generated
        self.assertTrue(electronic_payroll.xml_file, 
                        "Electronic payroll XML was not generated")
        self.assertTrue(electronic_payroll.pdf_file, 
                        "Electronic payroll PDF was not generated")

    def test_pila_report(self):
        """Test the generation of PILA (social security) report."""
        # Create PILA document
        pila = self.env['hr.pila'].create({
            'name': 'PILA de Prueba',
            'company_id': self.company.id,
            'period_id': self.env['hr.period'].search([], limit=1).id,
        })
        
        # Generate PILA report
        pila.generate_pila_file()
        
        # Check if PILA was generated
        self.assertTrue(pila.file, "PILA file was not generated")
    def test_consolidated_reports(self):
        """Test the generation of consolidated payroll reports."""
        # Create wizard for consolidated reports
        wizard = self.env['hr.payroll.consolidated.report.wizard'].create({
            'date_from': date.today().replace(day=1) - relativedelta(months=3),
            'date_to': date.today(),
            'report_type': 'summary',  # Options: summary, detailed, analytical
            'company_id': self.company.id,
        })
        
        # Generate consolidated report
        result = wizard.generate_report()
        
        # Check if report was generated
        self.assertTrue(result, "Consolidated report was not generated")
        self.assertEqual(result.get('type'), 'ir.actions.report', 
                         "Action returned is not a report")

    def test_provision_reports(self):
        """Test the generation of provision reports (cesantías, prima, vacaciones)."""
        # Create provision calculation
        provision = self.env['hr.provision.calculation'].create({
            'name': 'Cálculo de Provisiones',
            'date_from': date.today().replace(day=1),
            'date_to': date.today(),
            'provision_type': 'all',  # Options: all, severance, prima, vacation
            'company_id': self.company.id,
        })
        
        # Calculate provisions
        provision.calculate_provisions()
        
        # Generate provision report
        report_action = provision.print_report()
        
        # Check if report was generated
        self.assertTrue(report_action, "Provision report was not generated")
        self.assertEqual(report_action.get('type'), 'ir.actions.report', 
                         "Action returned is not a report")

    def test_work_certificate(self):
        """Test the generation of work certificate."""
        # Create wizard for work certificate
        wizard = self.env['hr.work.certificate.wizard'].create({
            'employee_id': self.employee.id,
            'date': date.today(),
            'include_salary': True,
            'company_id': self.company.id,
        })
        
        # Generate work certificate
        result = wizard.generate_certificate()
        
        # Check if certificate was generated
        self.assertTrue(result, "Work certificate was not generated")
        self.assertEqual(result.get('type'), 'ir.actions.report', 
                         "Action returned is not a report")

    def test_vacation_report(self):
        """Test the generation of vacation reports."""
        # Create vacation record
        vacation = self.env['hr.leave'].create({
            'name': 'Vacaciones',
            'employee_id': self.employee.id,
            'holiday_status_id': self.env.ref('hr_holidays.holiday_status_sl').id,
            'date_from': date.today() + relativedelta(days=10),
            'date_to': date.today() + relativedelta(days=25),
            'number_of_days': 15,
        })
        
        # Approve vacation
        vacation.action_approve()
        
        # Generate vacation report
        report_action = vacation.action_print_vacation()
        
        # Check if report was generated
        self.assertTrue(report_action, "Vacation report was not generated")
        self.assertEqual(report_action.get('type'), 'ir.actions.report', 
                         "Action returned is not a report")

    def test_payroll_analysis_report(self):
        """Test the generation of payroll analysis report."""
        # Create wizard for payroll analysis
        wizard = self.env['hr.payroll.analysis.report.wizard'].create({
            'date_from': date.today().replace(day=1) - relativedelta(months=6),
            'date_to': date.today(),
            'group_by': 'department',  # Options: department, job, category
            'analysis_type': 'salary_components',  # Options: salary_components, deductions, net
            'company_id': self.company.id,
        })
        
        # Generate analysis report
        result = wizard.generate_report()
        
        # Check if report was generated
        self.assertTrue(result, "Payroll analysis report was not generated")
        self.assertEqual(result.get('type'), 'ir.actions.report', 
                         "Action returned is not a report")

    def test_electronic_payroll_batch_report(self):
        """Test the generation of electronic payroll batch report."""
        # Create electronic payroll batch
        batch = self.env['hr.electronic.payroll.batch'].create({
            'name': 'Lote de Nómina Electrónica',
            'date_start': date.today().replace(day=1),
            'date_end': date.today().replace(day=28),
            'company_id': self.company.id,
        })
        
        # Create electronic payroll documents
        electronic_payroll = self.env['hr.electronic.payroll'].create({
            'name': 'Nómina Electrónica de Prueba',
            'company_id': self.company.id,
            'date_start': date.today().replace(day=1),
            'date_end': date.today().replace(day=28),
            'batch_id': batch.id,
            'payslip_ids': [(4, self.payslip.id)]
        })
        
        # Generate batch report
        report_action = batch.action_print_summary()
        
        # Check if report was generated
        self.assertTrue(report_action, "Electronic payroll batch report was not generated")
        self.assertEqual(report_action.get('type'), 'ir.actions.report', 
                         "Action returned is not a report")

    def test_report_with_specific_rules(self):
        """Test reports with specific Colombian salary rules."""
        # Create payslip with specific Colombian concepts
        payslip = self.env['hr.payslip'].create({
            'name': 'Nómina con Conceptos Específicos',
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'struct_id': self.structure.id,
            'date_from': date.today().replace(day=1),
            'date_to': date.today().replace(day=28),
            'company_id': self.company.id,
        })
        
        # Compute payslip
        payslip.compute_sheet()
        
        # Add specific Colombian salary rules
        for line in payslip.line_ids:
            if line.code == 'BASIC':
                line.amount = 1500000.0
            elif line.code == 'HEX':  # Horas extra
                line.amount = 100000.0
            elif line.code == 'AUX_TRANS':  # Auxilio de transporte
                line.amount = 102854.0
            elif line.code == 'PRIMA':  # Prima de servicios
                line.amount = 133333.0
        
        payslip.action_payslip_done()
        
        # Generate detailed report
        report_action = payslip.action_print_detailed_payslip()
        
        # Check if report was generated with specific rules
        self.assertTrue(report_action, "Detailed payslip report was not generated")
        self.assertEqual(report_action.get('type'), 'ir.actions.report', 
                         "Action returned is not a report")
        
        # Verify specific Colombian concepts in report data
        report_data = self.env['hr.payslip.detailed.report'].search([
            ('payslip_id', '=', payslip.id)
        ])
        self.assertTrue(report_data, "Report data was not created")
        self.assertTrue(any(line.code == 'HEX' for line in report_data.line_ids), 
                        "Extra hours not found in report")
        self.assertTrue(any(line.code == 'AUX_TRANS' for line in report_data.line_ids), 
                        "Transport allowance not found in report")

    def test_edge_cases(self):
        """Test report generation for edge cases."""
        # Test with employee having no active contract
        self.contract.state = 'close'
        
        # Create wizard for income certificate with employee having no active contract
        wizard = self.env['hr.payroll.income.certificate.wizard'].create({
            'employee_id': self.employee.id,
            'year': date.today().year,
            'company_id': self.company.id,
        })
        
        # Should still generate report for historical data
        result = wizard.generate_report()
        self.assertTrue(result, "Income certificate for inactive employee was not generated")
        
        # Test with date range having no payslips
        wizard = self.env['hr.payroll.consolidated.report.wizard'].create({
            'date_from': date.today() - relativedelta(years=5),
            'date_to': date.today() - relativedelta(years=4),
            'report_type': 'summary',
            'company_id': self.company.id,
        })
        
        # Should generate empty report without error
        result = wizard.generate_report()
        self.assertTrue(result, "Empty consolidated report was not generated")