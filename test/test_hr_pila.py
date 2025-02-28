from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError


@tagged('post_install', '-at_install', 'pila', 'colombia')
class TestHrPila(TransactionCase):
    """Test cases for Colombian PILA (Planilla Integrada de Liquidación de Aportes) in Odoo v18."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test company
        cls.company = cls.env['res.company'].create({
            'name': 'Test Company CO',
            'country_id': self.env.ref('base.co').id,
            'vat': '900.123.456-7',
            'street': 'Calle 93 # 11-13',
            'city': 'Bogotá',
            'zip': '110221',
            'phone': '+57 601 123 4567',
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
        
        # Create employees with different characteristics for PILA testing
        cls.employee1 = cls.env['hr.employee'].create({
            'name': 'Empleado Regular',
            'identification_id': '1234567890',
            'gender': 'male',
            'birthday': '1990-01-01',
            'country_id': self.env.ref('base.co').id,
            'department_id': cls.department.id,
            'job_id': cls.job.id,
            'category_ids': [(4, cls.category_a.id)],
            'company_id': cls.company.id,
            # Colombian specific fields
            'identification_type': 'CC',  # Cédula de Ciudadanía
            'place_of_birth': 'Bogotá',
            'eps_id': cls.env.ref('nomina_colombia_v18.eps_nueva_eps').id,
            'pension_fund_id': cls.env.ref('nomina_colombia_v18.pension_fund_colpensiones').id,
            'severance_fund_id': cls.env.ref('nomina_colombia_v18.severance_fund_porvenir').id,
            'arl_id': cls.env.ref('nomina_colombia_v18.arl_positiva').id,
            'ccf_id': cls.env.ref('nomina_colombia_v18.ccf_compensar').id,
        })
        
        cls.employee2 = cls.env['hr.employee'].create({
            'name': 'Empleado Alto Riesgo',
            'identification_id': '0987654321',
            'gender': 'female',
            'birthday': '1985-05-15',
            'country_id': cls.env.ref('base.co').id,
            'department_id': cls.department.id,
            'job_id': cls.job.id,
            'company_id': cls.company.id,
            # Colombian specific fields
            'identification_type': 'CC',
            'place_of_birth': 'Medellín',
            'eps_id': cls.env.ref('nomina_colombia_v18.eps_sura').id,
            'pension_fund_id': cls.env.ref('nomina_colombia_v18.pension_fund_proteccion').id,
            'severance_fund_id': cls.env.ref('nomina_colombia_v18.severance_fund_fna').id,
            'arl_id': cls.env.ref('nomina_colombia_v18.arl_sura').id,
            'ccf_id': cls.env.ref('nomina_colombia_v18.ccf_cafam').id,
            'risk_type': 'IV',  # Alto riesgo
        })
        
        cls.employee3 = cls.env['hr.employee'].create({
            'name': 'Empleado Integral',
            'identification_id': '5678901234',
            'gender': 'male',
            'birthday': '1980-10-20',
            'country_id': cls.env.ref('base.co').id,
            'department_id': cls.department.id,
            'job_id': cls.job.id,
            'company_id': cls.company.id,
            # Colombian specific fields
            'identification_type': 'CC',
            'place_of_birth': 'Cali',
            'eps_id': cls.env.ref('nomina_colombia_v18.eps_sanitas').id,
            'pension_fund_id': cls.env.ref('nomina_colombia_v18.pension_fund_porvenir').id,
            'severance_fund_id': cls.env.ref('nomina_colombia_v18.severance_fund_porvenir').id,
            'arl_id': cls.env.ref('nomina_colombia_v18.arl_bolivar').id,
            'ccf_id': cls.env.ref('nomina_colombia_v18.ccf_colsubsidio').id,
            'integral_salary': True,
        })
        
        # Create contract types
        cls.contract_type_indefinite = cls.env['hr.contract.type'].create({
            'name': 'Contrato Indefinido',
            'colombia_type': 'indefinite',
        })
        
        cls.contract_type_fixed = cls.env['hr.contract.type'].create({
            'name': 'Contrato Término Fijo',
            'colombia_type': 'fixed',
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
        
        # Create contracts
        cls.contract1 = cls.env['hr.contract'].create({
            'name': 'Contrato Empleado Regular',
            'employee_id': cls.employee1.id,
            'job_id': cls.job.id,
            'type_id': cls.contract_type_indefinite.id,
            'wage': 1500000.0,  # SMLV 2023
            'state': 'open',  # v18 uses 'open' instead of 'running'
            'date_start': date.today() - relativedelta(months=6),
            'structure_type_id': cls.structure_type.id,  # New in v18
            'resource_calendar_id': cls.env.ref('resource.resource_calendar_std').id,
            'company_id': cls.company.id,
            # Colombian specific fields
            'transport_allowance': True,
            'integral_salary': False,
            'high_risk_pension': False,
        })
        
        cls.contract2 = cls.env['hr.contract'].create({
            'name': 'Contrato Empleado Alto Riesgo',
            'employee_id': cls.employee2.id,
            'job_id': cls.job.id,
            'type_id': cls.contract_type_fixed.id,
            'wage': 2000000.0,
            'state': 'open',
            'date_start': date.today() - relativedelta(months=3),
            'date_end': date.today() + relativedelta(months=9),
            'structure_type_id': cls.structure_type.id,
            'resource_calendar_id': cls.env.ref('resource.resource_calendar_std').id,
            'company_id': cls.company.id,
            # Colombian specific fields
            'transport_allowance': True,
            'integral_salary': False,
            'high_risk_pension': True,
        })
        
        cls.contract3 = cls.env['hr.contract'].create({
            'name': 'Contrato Empleado Integral',
            'employee_id': cls.employee3.id,
            'job_id': cls.job.id,
            'type_id': cls.contract_type_indefinite.id,
            'wage': 13000000.0,  # Salario integral (> 10 SMLV)
            'state': 'open',
            'date_start': date.today() - relativedelta(months=12),
            'structure_type_id': cls.structure_type.id,
            'resource_calendar_id': cls.env.ref('resource.resource_calendar_std').id,
            'company_id': cls.company.id,
            # Colombian specific fields
            'transport_allowance': False,
            'integral_salary': True,
            'high_risk_pension': False,
        })
        
        # Create payroll period
        cls.period = cls.env['hr.period'].create({
            'name': 'Periodo ' + date.today().strftime('%B %Y'),
            'date_start': date.today().replace(day=1),
            'date_end': (date.today().replace(day=1) + relativedelta(months=1, days=-1)),
            'schedule_pay': 'monthly',
            'company_id': cls.company.id,
        })
        
        # Create payslips
        cls.payslip1 = cls.env['hr.payslip'].create({
            'name': 'Nómina Empleado Regular',
            'employee_id': cls.employee1.id,
            'contract_id': cls.contract1.id,
            'struct_id': cls.structure.id,
            'date_from': cls.period.date_start,
            'date_to': cls.period.date_end,
            'company_id': cls.company.id,
        })
        
        cls.payslip2 = cls.env['hr.payslip'].create({
            'name': 'Nómina Empleado Alto Riesgo',
            'employee_id': cls.employee2.id,
            'contract_id': cls.contract2.id,
            'struct_id': cls.structure.id,
            'date_from': cls.period.date_start,
            'date_to': cls.period.date_end,
            'company_id': cls.company.id,
        })
        
        cls.payslip3 = cls.env['hr.payslip'].create({
            'name': 'Nómina Empleado Integral',
            'employee_id': cls.employee3.id,
            'contract_id': cls.contract3.id,
            'struct_id': cls.structure.id,
            'date_from': cls.period.date_start,
            'date_to': cls.period.date_end,
            'company_id': cls.company.id,
        })
        
        # Compute payslips
        cls.payslip1.compute_sheet()
        cls.payslip2.compute_sheet()
        cls.payslip3.compute_sheet()
        
        # Confirm payslips
        cls.payslip1.action_payslip_done()
        cls.payslip2.action_payslip_done()
        cls.payslip3.action_payslip_done()
        
        # Create PILA operator
        cls.pila_operator = cls.env['hr.pila.operator'].create({
            'name': 'Operador PILA Test',
            'code': 'TEST01',
            'company_id': cls.company.id,
        })

    def test_01_create_pila(self):
        """Test the creation of a PILA record."""
        pila = self.env['hr.pila'].create({
            'name': 'PILA Test ' + date.today().strftime('%B %Y'),
            'period_id': self.period.id,
            'operator_id': self.pila_operator.id,
            'company_id': self.company.id,
        })
        
        self.assertTrue(pila, "PILA record was not created")
        self.assertEqual(pila.state, 'draft', "PILA should be in draft state")
        self.assertEqual(pila.period_id, self.period, "PILA period is incorrect")

    def test_02_load_employees(self):
        """Test loading employees into a PILA record."""
        pila = self.env['hr.pila'].create({
            'name': 'PILA Test ' + date.today().strftime('%B %Y'),
            'period_id': self.period.id,
            'operator_id': self.pila_operator.id,
            'company_id': self.company.id,
        })
        
        # Load employees
        pila.action_load_employees()
        
        self.assertTrue(pila.line_ids, "PILA lines were not created")
        self.assertEqual(len(pila.line_ids), 3, "Should have 3 PILA lines")
        
        # Check employee details
        employee1_line = pila.line_ids.filtered(lambda l: l.employee_id == self.employee1)
        self.assertTrue(employee1_line, "Employee 1 line not found")
        self.assertEqual(employee1_line.identification_id, '1234567890', "Wrong identification")
        self.assertEqual(employee1_line.eps_id, self.employee1.eps_id, "Wrong EPS")
        self.assertEqual(employee1_line.pension_fund_id, self.employee1.pension_fund_id, "Wrong pension fund")
        
        # Check high risk employee
        employee2_line = pila.line_ids.filtered(lambda l: l.employee_id == self.employee2)
        self.assertTrue(employee2_line, "Employee 2 line not found")
        self.assertTrue(employee2_line.high_risk_pension, "High risk pension flag not set")
        
        # Check integral salary employee
        employee3_line = pila.line_ids.filtered(lambda l: l.employee_id == self.employee3)
        self.assertTrue(employee3_line, "Employee 3 line not found")
        self.assertTrue(employee3_line.integral_salary, "Integral salary flag not set")

    def test_03_calculate_contributions(self):
        """Test calculation of social security contributions."""
        pila = self.env['hr.pila'].create({
            'name': 'PILA Test ' + date.today().strftime('%B %Y'),
            'period_id': self.period.id,
            'operator_id': self.pila_operator.id,
            'company_id': self.company.id,
        })
        
        # Load employees
        pila.action_load_employees()
        
        # Calculate contributions
        pila.action_calculate()
        
        # Check that contributions were calculated
        self.assertEqual(pila.state, 'calculated', "PILA should be in calculated state")
        
        # Check regular employee contributions
        employee1_line = pila.line_ids.filtered(lambda l: l.employee_id == self.employee1)
        self.assertTrue(employee1_line.ibc_health > 0, "IBC health not calculated")
        self.assertTrue(employee1_line.ibc_pension > 0, "IBC pension not calculated")
        self.assertTrue(employee1_line.ibc_arl > 0, "IBC ARL not calculated")
        self.assertTrue(employee1_line.ibc_parafiscal > 0, "IBC parafiscal not calculated")
        
        # Regular employee should have standard rates
        self.assertEqual(employee1_line.health_employee_rate, 4.0, "Wrong health employee rate")
        self.assertEqual(employee1_line.health_company_rate, 8.5, "Wrong health company rate")
        self.assertEqual(employee1_line.pension_employee_rate, 4.0, "Wrong pension employee rate")
        self.assertEqual(employee1_line.pension_company_rate, 12.0, "Wrong pension company rate")
        
        # Check high risk employee contributions
        employee2_line = pila.line_ids.filtered(lambda l: l.employee_id == self.employee2)
        self.assertTrue(employee2_line.high_risk_pension, "High risk pension flag not set")
        self.assertEqual(employee2_line.pension_company_rate, 22.0, "Wrong high risk pension company rate")
        
        # Check ARL rate based on risk type
        self.assertEqual(employee2_line.arl_rate, 4.35, "Wrong ARL rate for risk type IV")
        
        # Check integral salary employee contributions
        employee3_line = pila.line_ids.filtered(lambda l: l.employee_id == self.employee3)
        self.assertTrue(employee3_line.integral_salary, "Integral salary flag not set")
        
        # IBC for integral salary should be 70% of wage
        expected_ibc = employee3_line.wage * 0.7
        self.assertAlmostEqual(employee3_line.ibc_health, expected_ibc, delta=1.0, 
                              msg="Wrong IBC health for integral salary")
        
        # Check total contributions
        self.assertTrue(pila.total_health > 0, "Total health contribution not calculated")
        self.assertTrue(pila.total_pension > 0, "Total pension contribution not calculated")
        self.assertTrue(pila.total_arl > 0, "Total ARL contribution not calculated")
        self.assertTrue(pila.total_parafiscal > 0, "Total parafiscal contribution not calculated")
        self.assertTrue(pila.total_amount > 0, "Total amount not calculated")

    def test_04_generate_pila_file(self):
        """Test generation of PILA file."""
        pila = self.env['hr.pila'].create({
            'name': 'PILA Test ' + date.today().strftime('%B %Y'),
            'period_id': self.period.id,
            'operator_id': self.pila_operator.id,
            'company_id': self.company.id,
        })
        
        # Load employees and calculate
        pila.action_load_employees()
        pila.action_calculate()
        
        # Generate PILA file
        pila.action_generate_file()
        
        # Check that file was generated
        self.assertTrue(pila.file, "PILA file was not generated")
        self.assertEqual(pila.state, 'done', "PILA should be in done state")
        
        # Check file content
        file_content = pila.file.decode('utf-8')
        
        # File should contain company NIT
        self.assertIn('900123456', file_content, "File doesn't contain company NIT")
        
        # File should contain employee identification
        self.assertIn('1234567890', file_content, "File doesn't contain employee identification")
        
        # File should contain EPS and pension fund codes
        eps_code = self.employee1.eps_id.code
        pension_code = self.employee1.pension_fund_id.code
        self.assertIn(eps_code, file_content, "File doesn't contain EPS code")
        self.assertIn(pension_code, file_content, "File doesn't contain pension fund code")

    def test_05_pila_with_noveltys(self):
        """Test PILA with employee noveltys (vacations, incapacities, etc.)."""
        # Create leave type for vacation
        leave_type_vacation = self.env['hr.leave.type'].create({
            'name': 'Vacaciones',
            'allocation_type': 'fixed',
            'request_unit': 'day',
            'validity_start': False,
        })
        
        # Create leave type for incapacity
        leave_type_incapacity = self.env['hr.leave.type'].create({
            'name': 'Incapacidad EG',
            'allocation_type': 'no',
            'request_unit': 'day',
            'validity_start': False,
            'is_sick_leave': True,
        })
        
        # Create vacation for employee 1
        vacation = self.env['hr.leave'].create({
            'name': 'Vacaciones',
            'employee_id': self.employee1.id,
            'holiday_status_id': leave_type_vacation.id,
            'date_from': self.period.date_start + relativedelta(days=5),
            'date_to': self.period.date_start + relativedelta(days=15),
            'number_of_days': 10,
        })
        vacation.action_approve()
        
        # Create incapacity for employee 2
        incapacity = self.env['hr.leave'].create({
            'name': 'Incapacidad',
            'employee_id': self.employee2.id,
            'holiday_status_id': leave_type_incapacity.id,
            'date_from': self.period.date_start + relativedelta(days=10),
            'date_to': self.period.date_start + relativedelta(days=20),
            'number_of_days': 10,
        })
        incapacity.action_approve()
        
        # Create PILA
        pila = self.env['hr.pila'].create({
            'name': 'PILA Test with Noveltys',
            'period_id': self.period.id,
            'operator_id': self.pila_operator.id,
            'company_id': self.company.id,
        })
        
        # Load employees
        pila.action_load_employees()
        
        # Check that noveltys were loaded
        employee1_line = pila.line_ids.filtered(lambda l: l.employee_id == self.employee1)
        self.assertTrue(employee1_line.vacation_days > 0, "Vacation days not loaded")
        self.assertEqual(employee1_line.vacation_days, 10, "Wrong vacation days")
        
        employee2_line = pila.line_ids.filtered(lambda l: l.employee_id == self.employee2)
        self.assertTrue(employee2_line.incapacity_days > 0, "Incapacity days not loaded")
        self.assertEqual(employee2_line.incapacity_days, 10, "Wrong incapacity days")
        
        # Calculate contributions
        pila.action_calculate()
        
        # Check that IBC was adjusted for noveltys
        # For vacations, IBC should be adjusted proportionally
        expected_ibc1 = (employee1_line.wage * (30 - employee1_line.vacation_days) / 30) + employee1_line.vacation_value
        self.assertAlmostEqual(employee1_line.ibc_health, expected_ibc1, delta=1000.0, 
                              msg="IBC health not adjusted for vacations")
        
        # For incapacities, IBC should be adjusted proportionally
        expected_ibc2 = (employee2_line.wage * (30 - employee2_line.incapacity_days) / 30) + employee2_line.incapacity_value
        self.assertAlmostEqual(employee2_line.ibc_health, expected_ibc2, delta=1000.0, 
                              msg="IBC health not adjusted for incapacities")

    def test_06_pila_with_new_employee(self):
        """Test PILA with a new employee (ingreso)."""
        # Create new employee that started this month
        new_employee = self.env['hr.employee'].create({
            'name': 'Empleado Nuevo',
            'identification_id': '1122334455',
            'gender': 'male',
            'birthday': '1995-03-15',
            'country_id': cls.env.ref('base.co').id,
            'department_id': self.department.id,
            'job_id': self.job.id,
            'company_id': self.company.id,
            # Colombian specific fields
            'identification_type': 'CC',
            'place_of_birth': 'Barranquilla',
            'eps_id': self.env.ref('nomina_colombia_v18.eps_sanitas').id,
            'pension_fund_id': self.env.ref('nomina_colombia_v18.pension_fund_porvenir').id,
            'severance_fund_id': self.env.ref('nomina_colombia_v18.severance_fund_porvenir').id,
            'arl_id': self.env.ref('nomina_colombia_v18.arl_sura').id,
            'ccf_id': self.env.ref('nomina_colombia_v18.ccf_compensar').id,
        })
        
        # Create contract that starts during the current period
        new_contract = self.env['hr.contract'].create({
            'name': 'Contrato Empleado Nuevo',
            'employee_id': new_employee.id,
            'job_id': self.job.id,
            'type_id': self.contract_type_indefinite.id,
            'wage': 1800000.0,
            'state': 'open',
            'date_start': self.period.date_start + relativedelta(days=15),  # Mid-month start
            'structure_type_id': self.structure_type.id,
            'resource_calendar_id': self.env.ref('resource.resource_calendar_std').id,
            'company_id': self.company.id,
            'transport_allowance': True,
        })
        
        # Create payslip for new employee
        new_payslip = self.env['hr.payslip'].create({
            'name': 'Nómina Empleado Nuevo',
            'employee_id': new_employee.id,
            'contract_id': new_contract.id,
            'struct_id': self.structure.id,
            'date_from': new_contract.date_start,
            'date_to': self.period.date_end,
            'company_id': self.company.id,
        })
        
        # Compute and confirm payslip
        new_payslip.compute_sheet()
        new_payslip.action_payslip_done()
        
        # Create PILA
        pila = self.env['hr.pila'].create({
            'name': 'PILA Test with New Employee',
            'period_id': self.period.id,
            'operator_id': self.pila_operator.id,
            'company_id': self.company.id,
        })
        
        # Load employees
        pila.action_load_employees()
        
        # Check that new employee was loaded
        new_employee_line = pila.line_ids.filtered(lambda l: l.employee_id == new_employee)
        self.assertTrue(new_employee_line, "New employee not loaded")
        
        # Check that ingreso novelty is set
        self.assertTrue(new_employee_line.is_ingreso, "Ingreso novelty not set")
        
        # Calculate contributions
        pila.action_calculate()
        
        # Check that IBC was calculated proportionally for partial month
        days_worked = (self.period.date_end - new_contract.date_start).days + 1
        expected_ibc = (new_employee_line.wage * days_worked / 30)
        self.assertAlmostEqual(new_employee_line.ibc_health, expected_ibc, delta=1000.0, 
                              msg="IBC health not calculated proportionally for new employee")

    def test_07_pila_with_retired_employee(self):
        """Test PILA with a retired employee (retiro)."""
        # Create employee that will retire
        retiring_employee = self.env['hr.employee'].create({
            'name': 'Empleado Retirado',
            'identification_id': '9988776655',
            'gender': 'female',
            'birthday': '1988-07-22',
            'country_id': cls.env.ref('base.co').id,
            'department_id': self.department.id,
            'job_id': self.job.id,
            'company_id': self.company.id,
            # Colombian specific fields
            'identification_type': 'CC',
            'place_of_birth': 'Cartagena',
            'eps_id': self.env.ref('nomina_colombia_v18.eps_nueva_eps').id,
            'pension_fund_id': self.env.ref('nomina_colombia_v18.pension_fund_colpensiones').id,
            'severance_fund_id': self.env.ref('nomina_colombia_v18.severance_fund_porvenir').id,
            'arl_id': self.env.ref('nomina_colombia_v18.arl_positiva').id,
            'ccf_id': self.env.ref('nomina_colombia_v18.ccf_compensar').id,
        })
        
        # Create contract that ends during the current period
        retiring_contract = self.env['hr.contract'].create({
            'name': 'Contrato Empleado Retirado',
            'employee_id': retiring_employee.id,
            'job_id': self.job.id,
            'type_id': self.contract_type_indefinite.id,
            'wage': 1600000.0,
            'state': 'open',
            'date_start': self.period.date_start - relativedelta(months=2),
            'date_end': self.period.date_start + relativedelta(days=10),  # Ends early in month
            'structure_type_id': self.structure_type.id,
            'resource_calendar_id': self.env.ref('resource.resource_calendar_std').id,
            'company_id': self.company.id,
            'transport_allowance': True,
        })
        
        # Create payslip for retiring employee
        retiring_payslip = self.env['hr.payslip'].create({
            'name': 'Nómina Empleado Retirado',
            'employee_id': retiring_employee.id,
            'contract_id': retiring_contract.id,
            'struct_id': self.structure.id,
            'date_from': self.period.date_start,
            'date_to': retiring_contract.date_end,
            'company_id': self.company.id,
        })
        
        # Compute and confirm payslip
        retiring_payslip.compute_sheet()
        retiring_payslip.action_payslip_done()
        
        # Close contract
        retiring_contract.state = 'close'
        
        # Create PILA
        pila = self.env['hr.pila'].create({
            'name': 'PILA Test with Retired Employee',
            'period_id': self.period.id,
            'operator_id': self.pila_operator.id,
            'company_id': self.company.id,
        })
        
        # Load employees
        pila.action_load_employees()
        
        # Check that retiring employee was loaded
        retiring_employee_line = pila.line_ids.filtered(lambda l: l.employee_id == retiring_employee)
        self.assertTrue(retiring_employee_line, "Retiring employee not loaded")
        
        # Check that retiro novelty is set
        self.assertTrue(retiring_employee_line.is_retiro, "Retiro novelty not set")
        
        # Calculate contributions
        pila.action_calculate()
        
        # Check that IBC was calculated proportionally for partial month
        days_worked = (retiring_contract.date_end - self.period.date_start).days + 1
        expected_ibc = (retiring_employee_line.wage * days_worked / 30)
        self.assertAlmostEqual(retiring_employee_line.ibc_health, expected_ibc, delta=1000.0, 
                              msg="IBC health not calculated proportionally for retiring employee")

    def test_08_pila_with_salary_change(self):
        """Test PILA with an employee who had a salary change during the period."""
        # Create employee with salary change
        salary_change_employee = self.env['hr.employee'].create({
            'name': 'Empleado Cambio Salario',
            'identification_id': '5544332211',
            'gender': 'male',
            'birthday': '1992-11-05',
            'country_id': cls.env.ref('base.co').id,
            'department_id': self.department.id,
            'job_id': self.job.id,
            'company_id': self.company.id,
            # Colombian specific fields
            'identification_type': 'CC',
            'place_of_birth': 'Pereira',
            'eps_id': self.env.ref('nomina_colombia_v18.eps_sura').id,
            'pension_fund_id': self.env.ref('nomina_colombia_v18.pension_fund_proteccion').id,
            'severance_fund_id': self.env.ref('nomina_colombia_v18.severance_fund_porvenir').id,
            'arl_id': self.env.ref('nomina_colombia_v18.arl_sura').id,
            'ccf_id': self.env.ref('nomina_colombia_v18.ccf_cafam').id,
        })
        
        # Create initial contract
        salary_change_contract = self.env['hr.contract'].create({
            'name': 'Contrato Empleado Cambio Salario',
            'employee_id': salary_change_employee.id,
            'job_id': self.job.id,
            'type_id': self.contract_type_indefinite.id,
            'wage': 1700000.0,
            'state': 'open',
            'date_start': self.period.date_start - relativedelta(months=3),
            'structure_type_id': self.structure_type.id,
            'resource_calendar_id': self.env.ref('resource.resource_calendar_std').id,
            'company_id': self.company.id,
            'transport_allowance': True,
        })
        
        # Create salary change record (mid-month)
        salary_change_date = self.period.date_start + relativedelta(days=15)
        
        # In v18, we use contract history for salary changes
        salary_change_contract.write({
            'wage': 2000000.0,  # New salary
        })
        
        # Create contract history record
        self.env['hr.contract.history'].create({
            'employee_id': salary_change_employee.id,
            'contract_id': salary_change_contract.id,
            'date': salary_change_date,
            'wage': 1700000.0,  # Old salary
            'state': 'open',
            'company_id': self.company.id,
        })
        
        # Create payslip for salary change employee
        salary_change_payslip = self.env['hr.payslip'].create({
            'name': 'Nómina Empleado Cambio Salario',
            'employee_id': salary_change_employee.id,
            'contract_id': salary_change_contract.id,
            'struct_id': self.structure.id,
            'date_from': self.period.date_start,
            'date_to': self.period.date_end,
            'company_id': self.company.id,
        })
        
        # Compute and confirm payslip
        salary_change_payslip.compute_sheet()
        salary_change_payslip.action_payslip_done()
        
        # Create PILA
        pila = self.env['hr.pila'].create({
            'name': 'PILA Test with Salary Change',
            'period_id': self.period.id,
            'operator_id': self.pila_operator.id,
            'company_id': self.company.id,
        })
        
        # Load employees
        pila.action_load_employees()
        
        # Check that salary change employee was loaded
        salary_change_employee_line = pila.line_ids.filtered(lambda l: l.employee_id == salary_change_employee)
        self.assertTrue(salary_change_employee_line, "Salary change employee not loaded")
        
        # Check that VSP (Variación Salario Permanente) novelty is set
        self.assertTrue(salary_change_employee_line.is_vsp, "VSP novelty not set")
        
        # Calculate contributions
        pila.action_calculate()
        
        # Check that IBC was calculated with weighted average of salaries
        days_before_change = (salary_change_date - self.period.date_start).days
        days_after_change = (self.period.date_end - salary_change_date).days + 1
        expected_ibc = ((1700000.0 * days_before_change) + (2000000.0 * days_after_change)) / 30
        self.assertAlmostEqual(salary_change_employee_line.ibc_health, expected_ibc, delta=1000.0, 
                              msg="IBC health not calculated correctly for salary change")

    def test_09_pila_validation_rules(self):
        """Test PILA validation rules."""
        # Create PILA
        pila = self.env['hr.pila'].create({
            'name': 'PILA Test Validation',
            'period_id': self.period.id,
            'operator_id': self.pila_operator.id,
            'company_id': self.company.id,
        })
        
        # Load employees
        pila.action_load_employees()
        
        # Get a line to test validation
        line = pila.line_ids[0]
        
        # Test IBC validation - IBC cannot be less than minimum wage
        line.ibc_health = 100000  # Below minimum wage
        
        with self.assertRaises(ValidationError):
            pila.action_validate()
        
        # Fix IBC
        line.ibc_health = 1500000
        
        # Test missing EPS validation
        original_eps = line.eps_id
        line.eps_id = False
        
        with self.assertRaises(ValidationError):
            pila.action_validate()
        
        # Fix EPS
        line.eps_id = original_eps
        
        # Test missing pension fund validation
        original_pension = line.pension_fund_id
        line.pension_fund_id = False
        
        with self.assertRaises(ValidationError):
            pila.action_validate()
        
        # Fix pension fund
        line.pension_fund_id = original_pension
        
        # Test successful validation
        pila.action_validate()
        self.assertEqual(pila.state, 'validated', "PILA should be in validated state")

    def test_10_pila_workflow(self):
        """Test complete PILA workflow."""
        # Create PILA
        pila = self.env['hr.pila'].create({
            'name': 'PILA Test Workflow',
            'period_id': self.period.id,
            'operator_id': self.pila_operator.id,
            'company_id': self.company.id,
        })
        
        # Initial state should be draft
        self.assertEqual(pila.state, 'draft', "Initial state should be draft")
        
        # Load employees
        pila.action_load_employees()
        self.assertTrue(pila.line_ids, "Employees should be loaded")
        
        # Calculate contributions
        pila.action_calculate()
        self.assertEqual(pila.state, 'calculated', "State should be calculated")
        
        # Validate PILA
        pila.action_validate()
        self.assertEqual(pila.state, 'validated', "State should be validated")
        
        # Generate file
        pila.action_generate_file()
        self.assertEqual(pila.state, 'done', "State should be done")
        self.assertTrue(pila.file, "File should be generated")
        
        # Test reset to draft
        pila.action_reset_draft()
        self.assertEqual(pila.state, 'draft', "State should be reset to draft")
        
        # Test cancellation
        pila.action_cancel()
        self.assertEqual(pila.state, 'cancelled', "State should be cancelled")

    def test_11_pila_report(self):
        """Test PILA report generation."""
        # Create PILA
        pila = self.env['hr.pila'].create({
            'name': 'PILA Test Report',
            'period_id': self.period.id,
            'operator_id': self.pila_operator.id,
            'company_id': self.company.id,
        })
        
        # Load employees and calculate
        pila.action_load_employees()
        pila.action_calculate()
        
        # Generate report
        report_action = pila.print_report()
        
        # Check report action
        self.assertTrue(report_action, "Report action should be returned")
        self.assertEqual(report_action.get('type'), 'ir.actions.report', "Action should be a report")
        
        # Generate summary report
        summary_action = pila.print_summary()
        
        # Check summary report action
        self.assertTrue(summary_action, "Summary report action should be returned")
        self.assertEqual(summary_action.get('type'), 'ir.actions.report', "Action should be a report")

    def test_12_pila_with_multiple_contracts(self):
        """Test PILA with an employee who has multiple contracts in the period."""
        # Create employee with multiple contracts
        multi_contract_employee = self.env['hr.employee'].create({
            'name': 'Empleado Multi Contrato',
            'identification_id': '1357924680',
            'gender': 'male',
            'birthday': '1990-06-15',
            'country_id': cls.env.ref('base.co').id,
            'department_id': self.department.id,
            'job_id': self.job.id,
            'company_id': self.company.id,
            # Colombian specific fields
            'identification_type': 'CC',
            'place_of_birth': 'Bucaramanga',
            'eps_id': self.env.ref('nomina_colombia_v18.eps_sanitas').id,
            'pension_fund_id': self.env.ref('nomina_colombia_v18.pension_fund_porvenir').id,
            'severance_fund_id': self.env.ref('nomina_colombia_v18.severance_fund_porvenir').id,
            'arl_id': self.env.ref('nomina_colombia_v18.arl_sura').id,
            'ccf_id': self.env.ref('nomina_colombia_v18.ccf_compensar').id,
        })
        
        # Create first contract (ended early in the month)
        first_contract = self.env['hr.contract'].create({
            'name': 'Primer Contrato',
            'employee_id': multi_contract_employee.id,
            'job_id': self.job.id,
            'type_id': self.contract_type_fixed.id,
            'wage': 1600000.0,
            'state': 'close',  # Contract ended
            'date_start': self.period.date_start - relativedelta(months=2),
            'date_end': self.period.date_start + relativedelta(days=10),
            'structure_type_id': self.structure_type.id,
            'resource_calendar_id': self.env.ref('resource.resource_calendar_std').id,
            'company_id': self.company.id,
            'transport_allowance': True,
        })
        
        # Create second contract (started later in the month)
        second_contract = self.env['hr.contract'].create({
            'name': 'Segundo Contrato',
            'employee_id': multi_contract_employee.id,
            'job_id': self.job.id,
            'type_id': self.contract_type_indefinite.id,
            'wage': 1800000.0,
            'state': 'open',
            'date_start': self.period.date_start + relativedelta(days=20),
            'structure_type_id': self.structure_type.id,
            'resource_calendar_id': self.env.ref('resource.resource_calendar_std').id,
            'company_id': self.company.id,
            'transport_allowance': True,
        })
        
        # Create payslips for both contracts
        first_payslip = self.env['hr.payslip'].create({
            'name': 'Nómina Primer Contrato',
            'employee_id': multi_contract_employee.id,
            'contract_id': first_contract.id,
            'struct_id': self.structure.id,
            'date_from': self.period.date_start,
            'date_to': first_contract.date_end,
            'company_id': self.company.id,
        })
        
        second_payslip = self.env['hr.payslip'].create({
            'name': 'Nómina Segundo Contrato',
            'employee_id': multi_contract_employee.id,
            'contract_id': second_contract.id,
            'struct_id': self.structure.id,
            'date_from': second_contract.date_start,
            'date_to': self.period.date_end,
            'company_id': self.company.id,
        })
        
        # Compute and confirm payslips
        first_payslip.compute_sheet()
        first_payslip.action_payslip_done()
        
        second_payslip.compute_sheet()
        second_payslip.action_payslip_done()
        
        # Create PILA
        pila = self.env['hr.pila'].create({
            'name': 'PILA Test Multiple Contracts',
            'period_id': self.period.id,
            'operator_id': self.pila_operator.id,
            'company_id': self.company.id,
        })
        
        # Load employees
        pila.action_load_employees()
        
        # Check that employee with multiple contracts was loaded correctly
        multi_contract_lines = pila.line_ids.filtered(lambda l: l.employee_id == multi_contract_employee)
        self.assertEqual(len(multi_contract_lines), 1, "Should have one consolidated line for employee with multiple contracts")
        
        multi_contract_line = multi_contract_lines[0]
        
        # Check that both retiro and ingreso noveltys are set
        self.assertTrue(multi_contract_line.is_retiro, "Retiro novelty should be set")
        self.assertTrue(multi_contract_line.is_ingreso, "Ingreso novelty should be set")
        
        # Calculate contributions
        pila.action_calculate()
        
        # Check that IBC was calculated correctly combining both contracts
        days_first_contract = (first_contract.date_end - self.period.date_start).days + 1
        days_second_contract = (self.period.date_end - second_contract.date_start).days + 1
        days_gap = (second_contract.date_start - first_contract.date_end).days - 1
        
        expected_ibc = ((first_contract.wage * days_first_contract) + 
                        (second_contract.wage * days_second_contract)) / 30
        
        self.assertAlmostEqual(multi_contract_line.ibc_health, expected_ibc, delta=1000.0, 
                              msg="IBC health not calculated correctly for multiple contracts")

    def test_13_pila_with_suspended_contract(self):
        """Test PILA with an employee who has a suspended contract."""
        # Create employee with suspended contract
        suspended_employee = self.env['hr.employee'].create({
            'name': 'Empleado Suspendido',
            'identification_id': '2468013579',
            'gender': 'female',
            'birthday': '1993-09-25',
            'country_id': cls.env.ref('base.co').id,
            'department_id': self.department.id,
            'job_id': self.job.id,
            'company_id': self.company.id,
            # Colombian specific fields
            'identification_type': 'CC',
            'place_of_birth': 'Armenia',
            'eps_id': self.env.ref('nomina_colombia_v18.eps_nueva_eps').id,
            'pension_fund_id': self.env.ref('nomina_colombia_v18.pension_fund_colpensiones').id,
            'severance_fund_id': self.env.ref('nomina_colombia_v18.severance_fund_porvenir').id,
            'arl_id': self.env.ref('nomina_colombia_v18.arl_positiva').id,
            'ccf_id': self.env.ref('nomina_colombia_v18.ccf_compensar').id,
        })
        
        # Create contract
        suspended_contract = self.env['hr.contract'].create({
            'name': 'Contrato Suspendido',
            'employee_id': suspended_employee.id,
            'job_id': self.job.id,
            'type_id': self.contract_type_indefinite.id,
            'wage': 1700000.0,
            'state': 'suspend',  # Suspended contract
            'date_start': self.period.date_start - relativedelta(months=4),
            'structure_type_id': self.structure_type.id,
            'resource_calendar_id': self.env.ref('resource.resource_calendar_std').id,
            'company_id': self.company.id,
            'transport_allowance': True,
        })
        
        # Create suspension record
        suspension = self.env['hr.contract.suspension'].create({
            'name': 'Suspensión de Contrato',
            'employee_id': suspended_employee.id,
            'contract_id': suspended_contract.id,
            'date_start': self.period.date_start + relativedelta(days=5),
            'date_end': self.period.date_start + relativedelta(days=25),
            'suspension_type': 'SLN',  # Suspensión Licencia No Remunerada
            'company_id': self.company.id,
        })
        
        # Create payslip for suspended employee (partial month)
        suspended_payslip = self.env['hr.payslip'].create({
            'name': 'Nómina Empleado Suspendido',
            'employee_id': suspended_employee.id,
            'contract_id': suspended_contract.id,
            'struct_id': self.structure.id,
            'date_from': self.period.date_start,
            'date_to': self.period.date_end,
            'company_id': self.company.id,
        })
        
        # Compute and confirm payslip
        suspended_payslip.compute_sheet()
        suspended_payslip.action_payslip_done()
        
        # Create PILA
        pila = self.env['hr.pila'].create({
            'name': 'PILA Test Suspended Contract',
            'period_id': self.period.id,
            'operator_id': self.pila_operator.id,
            'company_id': self.company.id,
        })
        
        # Load employees
        pila.action_load_employees()
        
        # Check that suspended employee was loaded
        suspended_employee_line = pila.line_ids.filtered(lambda l: l.employee_id == suspended_employee)
        self.assertTrue(suspended_employee_line, "Suspended employee not loaded")
        
        # Check that SLN (Suspensión Licencia No Remunerada) novelty is set
        self.assertTrue(suspended_employee_line.is_sln, "SLN novelty not set")
        self.assertEqual(suspended_employee_line.suspension_days, 21, "Wrong suspension days")
        
        # Calculate contributions
        pila.action_calculate()
        
        # Check that IBC was calculated only for days worked
        days_worked = 30 - suspended_employee_line.suspension_days
        expected_ibc = (suspended_employee_line.wage * days_worked / 30)
        self.assertAlmostEqual(suspended_employee_line.ibc_health, expected_ibc, delta=1000.0, 
                              msg="IBC health not calculated correctly for suspended contract")

    def test_14_pila_with_licencia_maternidad(self):
        """Test PILA with an employee on maternity leave."""
        # Create employee on maternity leave
        maternity_employee = self.env['hr.employee'].create({
            'name': 'Empleada Licencia Maternidad',
            'identification_id': '8642097531',
            'gender': 'female',
            'birthday': '1990-03-15',
            'country_id': cls.env.ref('base.co').id,
            'department_id': self.department.id,
            'job_id': self.job.id,
            'company_id': self.company.id,
            # Colombian specific fields
            'identification_type': 'CC',
            'place_of_birth': 'Manizales',
            'eps_id': self.env.ref('nomina_colombia_v18.eps_sura').id,
            'pension_fund_id': self.env.ref('nomina_colombia_v18.pension_fund_proteccion').id,
            'severance_fund_id': self.env.ref('nomina_colombia_v18.severance_fund_porvenir').id,
            'arl_id': self.env.ref('nomina_colombia_v18.arl_sura').id,
            'ccf_id': self.env.ref('nomina_colombia_v18.ccf_cafam').id,
        })
        
        # Create contract
        maternity_contract = self.env['hr.contract'].create({
            'name': 'Contrato Licencia Maternidad',
            'employee_id': maternity_employee.id,
            'job_id': self.job.id,
            'type_id': self.contract_type_indefinite.id,
            'wage': 1900000.0,
            'state': 'open',
            'date_start': self.period.date_start - relativedelta(months=12),
            'structure_type_id': self.structure_type.id,
            'resource_calendar_id': self.env.ref('resource.resource_calendar_std').id,
            'company_id': self.company.id,
            'transport_allowance': True,
        })
        
        # Create leave type for maternity leave
        leave_type_maternity = self.env['hr.leave.type'].create({
            'name': 'Licencia de Maternidad',
            'allocation_type': 'no',
            'request_unit': 'day',
            'validity_start': False,
            'is_maternity_leave': True,
        })
        
        # Create maternity leave
        maternity_leave = self.env['hr.leave'].create({
            'name': 'Licencia de Maternidad',
            'employee_id': maternity_employee.id,
            'holiday_status_id': leave_type_maternity.id,
            'date_from': self.period.date_start,
            'date_to': self.period.date_end,
            'number_of_days': 30,
        })
        maternity_leave.action_approve()
        
        # Create payslip for maternity employee
        maternity_payslip = self.env['hr.payslip'].create({
            'name': 'Nómina Licencia Maternidad',
            'employee_id': maternity_employee.id,
            'contract_id': maternity_contract.id,
            'struct_id': self.structure.id,
            'date_from': self.period.date_start,
            'date_to': self.period.date_end,
            'company_id': self.company.id,
        })
        
        # Compute and confirm payslip
        maternity_payslip.compute_sheet()
        maternity_payslip.action_payslip_done()
        
        # Create PILA
        pila = self.env['hr.pila'].create({
            'name': 'PILA Test Licencia Maternidad',
            'period_id': self.period.id,
            'operator_id': self.pila_operator.id,
            'company_id': self.company.id,
        })
        
        # Load employees
        pila.action_load_employees()
        
        # Check that maternity employee was loaded
        maternity_employee_line = pila.line_ids.filtered(lambda l: l.employee_id == maternity_employee)
        self.assertTrue(maternity_employee_line, "Maternity employee not loaded")
        
        # Check that LMA (Licencia de Maternidad) novelty is set
        self.assertTrue(maternity_employee_line.is_lma, "LMA novelty not set")
        self.assertEqual(maternity_employee_line.maternity_days, 30, "Wrong maternity days")
        
        # Calculate contributions
        pila.action_calculate()
        
        # For maternity leave, IBC should be the full salary
        self.assertAlmostEqual(maternity_employee_line.ibc_health, maternity_employee_line.wage, delta=1.0, 
                              msg="IBC health not calculated correctly for maternity leave")
        
        # Check that health and pension contributions are calculated
        self.assertTrue(maternity_employee_line.health_employee_value > 0, "Health employee contribution not calculated")
        self.assertTrue(maternity_employee_line.health_company_value > 0, "Health company contribution not calculated")
        self.assertTrue(maternity_employee_line.pension_employee_value > 0, "Pension employee contribution not calculated")
        self.assertTrue(maternity_employee_line.pension_company_value > 0, "Pension company contribution not calculated")

    def test_15_export_pila_to_excel(self):
        """Test exporting PILA data to Excel."""
        # Create PILA
        pila = self.env['hr.pila'].create({
            'name': 'PILA Test Excel Export',
            'period_id': self.period.id,
            'operator_id': self.pila_operator.id,
            'company_id': self.company.id,
        })
        
        # Load employees and calculate
        pila.action_load_employees()
        pila.action_calculate()
        
        # Export to Excel
        export_action = pila.action_export_excel()
        
        # Check export action
        self.assertTrue(export_action, "Export action should be returned")
        self.assertEqual(export_action.get('type'), 'ir.actions.act_url', "Action should be URL action")
        self.assertTrue(export_action.get('url'), "URL should be provided")
        self.assertTrue('xlsx' in export_action.get('url', ''), "URL should point to Excel file")