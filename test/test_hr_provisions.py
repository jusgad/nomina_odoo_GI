from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

@tagged('post_install', '-at_install', 'provisions', 'colombia')
class TestHrProvisions(TransactionCase):
    """Test cases for Colombian payroll provisions (cesantías, intereses de cesantías, prima, vacaciones) in Odoo v18."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test company
        cls.company = cls.env['res.company'].create({
            'name': 'Test Company CO',
            'country_id': cls.env.ref('base.co').id,
            'vat': '900.123.456-7',
            'street': 'Calle 93 # 11-13',
            'city': 'Bogotá',
            'zip': '110221',
            'phone': '+57 601 123 4567',
        })
        
        # Set current user's company
        cls.env.user.company_id = cls.company
        
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
        
        # Create employees with different characteristics for provisions testing
        cls.employee1 = cls.env['hr.employee'].create({
            'name': 'Empleado Regular',
            'identification_id': '1234567890',
            'gender': 'male',
            'birthday': '1990-01-01',
            'country_id': cls.env.ref('base.co').id,
            'department_id': cls.department.id,
            'job_id': cls.job.id,
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
            'name': 'Empleado Integral',
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
        })
        
        cls.employee3 = cls.env['hr.employee'].create({
            'name': 'Empleado Nuevo',
            'identification_id': '5678901234',
            'gender': 'male',
            'birthday': '1992-10-20',
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
        # Regular employee with more than 1 year
        cls.contract1 = cls.env['hr.contract'].create({
            'name': 'Contrato Empleado Regular',
            'employee_id': cls.employee1.id,
            'job_id': cls.job.id,
            'type_id': cls.contract_type_indefinite.id,
            'wage': 1500000.0,  # SMLV 2023
            'state': 'open',  # v18 uses 'open' instead of 'running'
            'date_start': date.today() - relativedelta(years=1, months=6),
            'structure_type_id': cls.structure_type.id,  # New in v18
            'resource_calendar_id': cls.env.ref('resource.resource_calendar_std').id,
            'company_id': cls.company.id,
            # Colombian specific fields
            'transport_allowance': True,
            'integral_salary': False,
        })
        
        # Integral salary employee
        cls.contract2 = cls.env['hr.contract'].create({
            'name': 'Contrato Empleado Integral',
            'employee_id': cls.employee2.id,
            'job_id': cls.job.id,
            'type_id': cls.contract_type_indefinite.id,
            'wage': 13000000.0,  # Salario integral (> 10 SMLV)
            'state': 'open',
            'date_start': date.today() - relativedelta(years=2),
            'structure_type_id': cls.structure_type.id,
            'resource_calendar_id': cls.env.ref('resource.resource_calendar_std').id,
            'company_id': cls.company.id,
            # Colombian specific fields
            'transport_allowance': False,
            'integral_salary': True,
        })
        
        # New employee with less than 1 year
        cls.contract3 = cls.env['hr.contract'].create({
            'name': 'Contrato Empleado Nuevo',
            'employee_id': cls.employee3.id,
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
        })
        
        # Create payroll periods for the last year
        cls.periods = []
        for i in range(12, 0, -1):
            period_date = date.today() - relativedelta(months=i)
            period = cls.env['hr.period'].create({
                'name': f'Periodo {period_date.strftime("%B %Y")}',
                'date_start': period_date.replace(day=1),
                'date_end': (period_date.replace(day=1) + relativedelta(months=1, days=-1)),
                'schedule_pay': 'monthly',
                'company_id': cls.company.id,
            })
            cls.periods.append(period)
        
        # Create current period
        cls.current_period = cls.env['hr.period'].create({
            'name': f'Periodo {date.today().strftime("%B %Y")}',
            'date_start': date.today().replace(day=1),
            'date_end': (date.today().replace(day=1) + relativedelta(months=1, days=-1)),
            'schedule_pay': 'monthly',
            'company_id': cls.company.id,
        })
        
        # Create payslips for the last year for employee1 and employee2
        for period in cls.periods:
            # Payslip for employee1
            payslip1 = cls.env['hr.payslip'].create({
                'name': f'Nómina {cls.employee1.name} - {period.name}',
                'employee_id': cls.employee1.id,
                'contract_id': cls.contract1.id,
                'struct_id': cls.structure.id,
                'date_from': period.date_start,
                'date_to': period.date_end,
                'company_id': cls.company.id,
            })
            payslip1.compute_sheet()
            payslip1.action_payslip_done()
            
            # Payslip for employee2
            payslip2 = cls.env['hr.payslip'].create({
                'name': f'Nómina {cls.employee2.name} - {period.name}',
                'employee_id': cls.employee2.id,
                'contract_id': cls.contract2.id,
                'struct_id': cls.structure.id,
                'date_from': period.date_start,
                'date_to': period.date_end,
                'company_id': cls.company.id,
            })
            payslip2.compute_sheet()
            payslip2.action_payslip_done()
        
        # Create payslips for the last 3 months for employee3
        for i in range(3):
            period = cls.periods[-i-1] if i < len(cls.periods) else cls.current_period
            payslip3 = cls.env['hr.payslip'].create({
                'name': f'Nómina {cls.employee3.name} - {period.name}',
                'employee_id': cls.employee3.id,
                'contract_id': cls.contract3.id,
                'struct_id': cls.structure.id,
                'date_from': period.date_start,
                'date_to': period.date_end,
                'company_id': cls.company.id,
            })
            payslip3.compute_sheet()
            payslip3.action_payslip_done()

    def test_01_create_provision_calculation(self):
        """Test the creation of a provision calculation."""
        provision = self.env['hr.provision.calculation'].create({
            'name': 'Cálculo de Provisiones',
            'date_from': date.today().replace(day=1) - relativedelta(months=1),
            'date_to': date.today().replace(day=1) - relativedelta(days=1),
            'provision_type': 'all',  # all, severance, severance_interest, prima, vacation
            'company_id': self.company.id,
        })
        
        self.assertTrue(provision, "Provision calculation was not created")
        self.assertEqual(provision.state, 'draft', "Provision should be in draft state")
        self.assertEqual(provision.provision_type, 'all', "Provision type is incorrect")

    def test_02_load_employees(self):
        """Test loading employees into a provision calculation."""
        provision = self.env['hr.provision.calculation'].create({
            'name': 'Cálculo de Provisiones',
            'date_from': date.today().replace(day=1) - relativedelta(months=1),
            'date_to': date.today().replace(day=1) - relativedelta(days=1),
            'provision_type': 'all',
            'company_id': self.company.id,
        })
        
        # Load employees
        provision.action_load_employees()
        
        self.assertTrue(provision.line_ids, "Provision lines were not created")
        self.assertEqual(len(provision.line_ids), 3, "Should have 3 provision lines")
        
        # Check employee details
        employee1_line = provision.line_ids.filtered(lambda l: l.employee_id == self.employee1)
        self.assertTrue(employee1_line, "Employee 1 line not found")
        self.assertEqual(employee1_line.contract_id, self.contract1, "Wrong contract")
        self.assertEqual(employee1_line.wage, 1500000.0, "Wrong wage")
        
        # Check integral salary employee
        employee2_line = provision.line_ids.filtered(lambda l: l.employee_id == self.employee2)
        self.assertTrue(employee2_line, "Employee 2 line not found")
        self.assertTrue(employee2_line.integral_salary, "Integral salary flag not set")
        
        # Check new employee
        employee3_line = provision.line_ids.filtered(lambda l: l.employee_id == self.employee3)
        self.assertTrue(employee3_line, "Employee 3 line not found")
        self.assertEqual(employee3_line.contract_id, self.contract3, "Wrong contract")
        self.assertEqual(employee3_line.date_start, self.contract3.date_start, "Wrong start date")

    def test_03_calculate_severance_provision(self):
        """Test calculation of severance (cesantías) provision."""
        provision = self.env['hr.provision.calculation'].create({
            'name': 'Cálculo de Cesantías',
            'date_from': date.today().replace(day=1) - relativedelta(months=1),
            'date_to': date.today().replace(day=1) - relativedelta(days=1),
            'provision_type': 'severance',
            'company_id': self.company.id,
        })
        
        # Load employees
        provision.action_load_employees()
        
        # Calculate provisions
        provision.action_calculate()
        
        # Check that provisions were calculated
        self.assertEqual(provision.state, 'calculated', "Provision should be in calculated state")
        
        # Check regular employee severance
        employee1_line = provision.line_ids.filtered(lambda l: l.employee_id == self.employee1)
        self.assertTrue(employee1_line.severance_value > 0, "Severance not calculated")
        
        # Regular employee should have severance based on salary + transport allowance
        expected_base = employee1_line.wage + employee1_line.transport_allowance
        expected_severance = expected_base * employee1_line.worked_days / 360
        self.assertAlmostEqual(employee1_line.severance_value, expected_severance, delta=1.0, 
                              msg="Wrong severance calculation")
        
        # Check integral salary employee severance
        employee2_line = provision.line_ids.filtered(lambda l: l.employee_id == self.employee2)
        self.assertTrue(employee2_line.integral_salary, "Integral salary flag not set")
        
        # Integral salary should use 70% of wage for severance calculation
        expected_base2 = employee2_line.wage * 0.7
        expected_severance2 = expected_base2 * employee2_line.worked_days / 360
        self.assertAlmostEqual(employee2_line.severance_value, expected_severance2, delta=1.0, 
                              msg="Wrong severance calculation for integral salary")
        
        # Check new employee severance (proportional to time worked)
        employee3_line = provision.line_ids.filtered(lambda l: l.employee_id == self.employee3)
        self.assertTrue(employee3_line.worked_days < 360, "New employee should have less than 360 worked days")
        
        expected_base3 = employee3_line.wage + employee3_line.transport_allowance
        expected_severance3 = expected_base3 * employee3_line.worked_days / 360
        self.assertAlmostEqual(employee3_line.severance_value, expected_severance3, delta=1.0, 
                              msg="Wrong severance calculation for new employee")

    def test_04_calculate_severance_interest_provision(self):
        """Test calculation of severance interest (intereses de cesantías) provision."""
        provision = self.env['hr.provision.calculation'].create({
            'name': 'Cálculo de Intereses de Cesantías',
            'date_from': date.today().replace(day=1) - relativedelta(months=1),
            'date_to': date.today().replace(day=1) - relativedelta(days=1),
            'provision_type': 'severance_interest',
            'company_id': self.company.id,
        })
        
        # Load employees
        provision.action_load_employees()
        
        # Calculate provisions
        provision.action_calculate()
        
        # Check that provisions were calculated
        self.assertEqual(provision.state, 'calculated', "Provision should be in calculated state")
        
        # Check regular employee severance interest
        employee1_line = provision.line_ids.filtered(lambda l: l.employee_id == self.employee1)
        self.assertTrue(employee1_line.severance_interest_value > 0, "Severance interest not calculated")
        
        # Severance interest should be 12% of severance value
        expected_base = employee1_line.wage + employee1_line.transport_allowance
        expected_severance = expected_base * employee1_line.worked_days / 360
        expected_interest = expected_severance * 0.12 * employee1_line.worked_days / 360
        self.assertAlmostEqual(employee1_line.severance_interest_value, expected_interest, delta=1.0, 
                              msg="Wrong severance interest calculation")
        
        # Check integral salary employee severance interest
        employee2_line = provision.line_ids.filtered(lambda l: l.employee_id == self.employee2)
        
        # Integral salary should use 70% of wage for severance calculation
        expected_base2 = employee2_line.wage * 0.7
        expected_severance2 = expected_base2 * employee2_line.worked_days / 360
        expected_interest2 = expected_severance2 * 0.12 * employee2_line.worked_days / 360
        self.assertAlmostEqual(employee2_line.severance_interest_value, expected_interest2, delta=1.0, 
                              msg="Wrong severance interest calculation for integral salary")
        
        # Check new employee severance interest (proportional to time worked)
        employee3_line = provision.line_ids.filtered(lambda l: l.employee_id == self.employee3)
        
        expected_base3 = employee3_line.wage + employee3_line.transport_allowance
        expected_severance3 = expected_base3 * employee3_line.worked_days / 360
        expected_interest3 = expected_severance3 * 0.12 * employee3_line.worked_days / 360
        self.assertAlmostEqual(employee3_line.severance_interest_value, expected_interest3, delta=1.0, 
                              msg="Wrong severance interest calculation for new employee")

    def test_05_calculate_prima_provision(self):
        """Test calculation of prima de servicios provision."""
        provision = self.env['hr.provision.calculation'].create({
            'name': 'Cálculo de Prima de Servicios',
            'date_from': date.today().replace(day=1) - relativedelta(months=1),
            'date_to': date.today().replace(day=1) - relativedelta(days=1),
            'provision_type': 'prima',
            'company_id': self.company.id,
        })
        
        # Load employees
        provision.action_load_employees()
        
        # Calculate provisions
        provision.action_calculate()
        
        # Check that provisions were calculated
        self.assertEqual(provision.state, 'calculated', "Provision should be in calculated state")
        
        # Check regular employee prima
        employee1_line = provision.line_ids.filtered(lambda l: l.employee_id == self.employee1)
        self.assertTrue(employee1_line.prima_value > 0, "Prima not calculated")
        
        # Prima should be calculated the same as severance
        expected_base = employee1_line.wage + employee1_line.transport_allowance
        expected_prima = expected_base * employee1_line.worked_days / 360
        self.assertAlmostEqual(employee1_line.prima_value, expected_prima, delta=1.0, 
                              msg="Wrong prima calculation")
        
        # Check integral salary employee prima
        employee2_line = provision.line_ids.filtered(lambda l: l.employee_id == self.employee2)
        
        # Integral salary should use 70% of wage for prima calculation
        expected_base2 = employee2_line.wage * 0.7
        expected_prima2 = expected_base2 * employee2_line.worked_days / 360
        self.assertAlmostEqual(employee2_line.prima_value, expected_prima2, delta=1.0, 
                              msg="Wrong prima calculation for integral salary")
        
        # Check new employee prima (proportional to time worked)
        employee3_line = provision.line_ids.filtered(lambda l: l.employee_id == self.employee3)
        
        expected_base3 = employee3_line.wage + employee3_line.transport_allowance
        expected_prima3 = expected_base3 * employee3_line.worked_days / 360
        self.assertAlmostEqual(employee3_line.prima_value, expected_prima3, delta=1.0, 
                              msg="Wrong prima calculation for new employee")

    def test_06_calculate_vacation_provision(self):
        """Test calculation of vacation provision."""
        provision = self.env['hr.provision.calculation'].create({
            'name': 'Cálculo de Vacaciones',
            'date_from': date.today().replace(day=1) - relativedelta(months=1),
            'date_to': date.today().replace(day=1) - relativedelta(days=1),
            'provision_type': 'vacation',
            'company_id': self.company.id,
        })
        
        # Load employees
        provision.action_load_employees()
        
        # Calculate provisions
        provision.action_calculate()
        
        # Check that provisions were calculated
        self.assertEqual(provision.state, 'calculated', "Provision should be in calculated state")
        
        # Check regular employee vacation
        employee1_line = provision.line_ids.filtered(lambda l: l.employee_id == self.employee1)
        self.assertTrue(employee1_line.vacation_value > 0, "Vacation not calculated")
        
        # Vacation should be based on salary only (no transport allowance)
        # 15 days per year = 15/360 = 0.041666...
        expected_vacation = employee1_line.wage * 15 / 360 * employee1_line.worked_days
        self.assertAlmostEqual(employee1_line.vacation_value, expected_vacation, delta=1.0, 
                              msg="Wrong vacation calculation")
        
        # Check integral salary employee vacation
        employee2_line = provision.line_ids.filtered(lambda l: l.employee_id == self.employee2)
        
        # Integral salary should use 70% of wage for vacation calculation
        expected_vacation2 = employee2_line.wage * 0.7 * 15 / 360 * employee2_line.worked_days
        self.assertAlmostEqual(employee2_line.vacation_value, expected_vacation2, delta=1.0, 
                              msg="Wrong vacation calculation for integral salary")
        
        # Check new employee vacation (proportional to time worked)
        employee3_line = provision.line_ids.filtered(lambda l: l.employee_id == self.employee3)
        
        expected_vacation3 = employee3_line.wage * 15 / 360 * employee3_line.worked_days
        self.assertAlmostEqual(employee3_line.vacation_value, expected_vacation3, delta=1.0, 
                              msg="Wrong vacation calculation for new employee")

    def test_07_calculate_all_provisions(self):
        """Test calculation of all provisions together."""
        provision = self.env['hr.provision.calculation'].create({
            'name': 'Cálculo de Todas las Provisiones',
            'date_from': date.today().replace(day=1) - relativedelta(months=1),
            'date_to': date.today().replace(day=1) - relativedelta(days=1),
            'provision_type': 'all',
            'company_id': self.company.id,
        })
        
        # Load employees
        provision.action_load_employees()
        
        # Calculate provisions
        provision.action_calculate()
        
        # Check that provisions were calculated
        self.assertEqual(provision.state, 'calculated', "Provision should be in calculated state")
        
        # Check regular employee all provisions
        employee1_line = provision.line_ids.filtered(lambda l: l.employee_id == self.employee1)
        self.assertTrue(employee1_line.severance_value > 0, "Severance not calculated")
        self.assertTrue(employee1_line.severance_interest_value > 0, "Severance interest not calculated")
        self.assertTrue(employee1_line.prima_value > 0, "Prima not calculated")
        self.assertTrue(employee1_line.vacation_value > 0, "Vacation not calculated")
        
        # Check total provision
        expected_total = (employee1_line.severance_value + 
                          employee1_line.severance_interest_value + 
                          employee1_line.prima_value + 
                          employee1_line.vacation_value)
        self.assertAlmostEqual(employee1_line.total_provision, expected_total, delta=1.0, 
                              msg="Wrong total provision calculation")
        
        # Check provision totals
        self.assertTrue(provision.total_severance > 0, "Total severance not calculated")
        self.assertTrue(provision.total_severance_interest > 0, "Total severance interest not calculated")
        self.assertTrue(provision.total_prima > 0, "Total prima not calculated")
        self.assertTrue(provision.total_vacation > 0, "Total vacation not calculated")
        self.assertTrue(provision.total_provision > 0, "Total provision not calculated")
        
        expected_grand_total = sum(line.total_provision for line in provision.line_ids)
        self.assertAlmostEqual(provision.total_provision, expected_grand_total, delta=1.0, 
                              msg="Wrong grand total provision calculation")

    def test_08_provision_with_salary_changes(self):
        """Test provisions calculation with salary changes during the period."""
        # Create employee with salary change
        salary_change_employee = self.env['hr.employee'].create({
            'name': 'Empleado Cambio Salario',
            'identification_id': '5544332211',
            'gender': 'male',
            'birthday': '1992-11-05',
            'country_id': self.env.ref('base.co').id,
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
            'date_start': date.today() - relativedelta(months=6),
            'structure_type_id': self.structure_type.id,
            'resource_calendar_id': self.env.ref('resource.resource_calendar_std').id,
            'company_id': self.company.id,
            'transport_allowance': True,
        })
        
        # Create payslips for first 3 months
        for i in range(3):
            period = self.periods[-6+i] if i < len(self.periods) else self.current_period
            payslip = self.env['hr.payslip'].create({
                'name': f'Nómina {salary_change_employee.name} - {period.name}',
                'employee_id': salary_change_employee.id,
                'contract_id': salary_change_contract.id,
                'struct_id': self.structure.id,
                'date_from': period.date_start,
                'date_to': period.date_end,
                'company_id': self.company.id,
            })
            payslip.compute_sheet()
            payslip.action_payslip_done()
        
        # Change salary after 3 months
        salary_change_date = date.today() - relativedelta(months=3)
        
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
        
        # Create payslips for next 3 months with new salary
        for i in range(3):
            period = self.periods[-3+i] if i < len(self.periods) else self.current_period
            payslip = self.env['hr.payslip'].create({
                'name': f'Nómina {salary_change_employee.name} - {period.name}',
                'employee_id': salary_change_employee.id,
                'contract_id': salary_change_contract.id,
                'struct_id': self.structure.id,
                'date_from': period.date_start,
                'date_to': period.date_end,
                'company_id': self.company.id,
            })
            payslip.compute_sheet()
            payslip.action_payslip_done()
        
        # Create provision calculation
        provision = self.env['hr.provision.calculation'].create({
            'name': 'Cálculo de Provisiones con Cambio Salarial',
            'date_from': date.today() - relativedelta(months=6),
            'date_to': date.today(),
            'provision_type': 'all',
            'company_id': self.company.id,
        })
        
        # Load employees
        provision.action_load_employees()
        
        # Check that salary change employee was loaded
        salary_change_line = provision.line_ids.filtered(lambda l: l.employee_id == salary_change_employee)
        self.assertTrue(salary_change_line, "Salary change employee not loaded")
        
        # Calculate provisions
        provision.action_calculate()
        
        # Check that provisions were calculated with weighted average salary
        # 3 months at 1700000 and 3 months at 2000000
        expected_avg_salary = (1700000.0 * 90 + 2000000.0 * 90) / 180
        self.assertAlmostEqual(salary_change_line.average_wage, expected_avg_salary, delta=100.0, 
                              msg="Wrong average wage calculation")
        
        # Check severance calculation with average salary
        expected_base = expected_avg_salary + salary_change_line.transport_allowance
        expected_severance = expected_base * salary_change_line.worked_days / 360
        self.assertAlmostEqual(salary_change_line.severance_value, expected_severance, delta=10000.0, 
                              msg="Wrong severance calculation with salary change")

    def test_09_provision_with_variable_salary(self):
        """Test provisions calculation with variable salary components."""
        # Create employee with variable salary
        variable_salary_employee = self.env['hr.employee'].create({
            'name': 'Empleado Salario Variable',
            'identification_id': '1122334455',
            'gender': 'female',
            'birthday': '1988-03-15',
            'country_id': self.env.ref('base.co').id,
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
        
        # Create contract with base salary
        variable_salary_contract = self.env['hr.contract'].create({
            'name': 'Contrato Salario Variable',
            'employee_id': variable_salary_employee.id,
            'job_id': self.job.id,
            'type_id': self.contract_type_indefinite.id,
            'wage': 1600000.0,  # Base salary
            'state': 'open',
            'date_start': date.today() - relativedelta(months=6),
            'structure_type_id': self.structure_type.id,
            'resource_calendar_id': self.env.ref('resource.resource_calendar_std').id,
            'company_id': self.company.id,
            'transport_allowance': True,
        })
        
        # Create salary rule for commissions
        commission_category = self.env['hr.salary.rule.category'].create({
            'name': 'Comisiones',
            'code': 'COM',
        })
        
        commission_rule = self.env['hr.salary.rule'].create({
            'name': 'Comisiones',
            'code': 'COM',
            'category_id': commission_category.id,
            'sequence': 30,
            'amount_select': 'code',
            'amount_python_compute': 'result = inputs.COM.amount if inputs.COM else 0',
            'struct_id': self.structure.id,
        })
        
        # Create payslips with variable commissions for last 6 months
        commission_amounts = [200000, 300000, 150000, 250000, 350000, 180000]
        
        for i, amount in enumerate(commission_amounts):
            period = self.periods[-6+i] if i < len(self.periods) else self.current_period
            
            # Create payslip
            payslip = self.env['hr.payslip'].create({
                'name': f'Nómina {variable_salary_employee.name} - {period.name}',
                'employee_id': variable_salary_employee.id,
                'contract_id': variable_salary_contract.id,
                'struct_id': self.structure.id,
                'date_from': period.date_start,
                'date_to': period.date_end,
                'company_id': self.company.id,
            })
            
            # Create payslip input for commission
            self.env['hr.payslip.input'].create({
                'name': 'Comisión',
                'payslip_id': payslip.id,
                'input_type_id': self.env.ref('hr_payroll.input_type_commission').id,
                'amount': amount,
                'code': 'COM',
            })
            
            payslip.compute_sheet()
            payslip.action_payslip_done()
        
        # Create provision calculation
        provision = self.env['hr.provision.calculation'].create({
            'name': 'Cálculo de Provisiones con Salario Variable',
            'date_from': date.today() - relativedelta(months=6),
            'date_to': date.today(),
            'provision_type': 'all',
            'company_id': self.company.id,
        })
        
        # Load employees
        provision.action_load_employees()
        
        # Check that variable salary employee was loaded
        variable_salary_line = provision.line_ids.filtered(lambda l: l.employee_id == variable_salary_employee)
        self.assertTrue(variable_salary_line, "Variable salary employee not loaded")
        
        # Calculate provisions
        provision.action_calculate()
        
        # Check that provisions were calculated including variable components
        # Average commission = sum(commission_amounts) / 6
        avg_commission = sum(commission_amounts) / 6
        expected_avg_salary = variable_salary_contract.wage + avg_commission
        self.assertAlmostEqual(variable_salary_line.average_wage, expected_avg_salary, delta=100.0, 
                              msg="Wrong average wage calculation with variable components")
        
        # Check severance calculation with average salary including commissions
        expected_base = expected_avg_salary + variable_salary_line.transport_allowance
        expected_severance = expected_base * variable_salary_line.worked_days / 360
        self.assertAlmostEqual(variable_salary_line.severance_value, expected_severance, delta=10000.0, 
                              msg="Wrong severance calculation with variable salary")

    def test_10_provision_with_time_off(self):
        """Test provisions calculation with time off periods."""
        # Create employee with time off
        time_off_employee = self.env['hr.employee'].create({
            'name': 'Empleado con Ausencias',
            'identification_id': '9988776655',
            'gender': 'male',
            'birthday': '1991-07-22',
            'country_id': self.env.ref('base.co').id,
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
        
        # Create contract
        time_off_contract = self.env['hr.contract'].create({
            'name': 'Contrato Empleado con Ausencias',
            'employee_id': time_off_employee.id,
            'job_id': self.job.id,
            'type_id': self.contract_type_indefinite.id,
            'wage': 1800000.0,
            'state': 'open',
            'date_start': date.today() - relativedelta(months=6),
            'structure_type_id': self.structure_type.id,
            'resource_calendar_id': self.env.ref('resource.resource_calendar_std').id,
            'company_id': self.company.id,
            'transport_allowance': True,
        })
        
        # Create leave types
        leave_type_vacation = self.env['hr.leave.type'].create({
            'name': 'Vacaciones',
            'allocation_type': 'fixed',
            'request_unit': 'day',
            'validity_start': False,
        })
        
        leave_type_unpaid = self.env['hr.leave.type'].create({
            'name': 'Licencia No Remunerada',
            'allocation_type': 'no',
            'request_unit': 'day',
            'validity_start': False,
            'unpaid': True,
        })
        
        # Create vacation (15 days, 3 months ago)
        vacation_start = date.today() - relativedelta(months=3, days=15)
        vacation_end = vacation_start + relativedelta(days=14)
        
        vacation = self.env['hr.leave'].create({
            'name': 'Vacaciones',
            'employee_id': time_off_employee.id,
            'holiday_status_id': leave_type_vacation.id,
            'date_from': vacation_start,
            'date_to': vacation_end,
            'number_of_days': 15,
        })
        vacation.action_approve()
        
        # Create unpaid leave (10 days, 1 month ago)
        unpaid_start = date.today() - relativedelta(months=1, days=10)
        unpaid_end = unpaid_start + relativedelta(days=9)
        
        unpaid = self.env['hr.leave'].create({
            'name': 'Licencia No Remunerada',
            'employee_id': time_off_employee.id,
            'holiday_status_id': leave_type_unpaid.id,
            'date_from': unpaid_start,
            'date_to': unpaid_end,
            'number_of_days': 10,
        })
        unpaid.action_approve()
        
        # Create payslips for last 6 months
        for i in range(6):
            period = self.periods[-6+i] if i < len(self.periods) else self.current_period
            
            payslip = self.env['hr.payslip'].create({
                'name': f'Nómina {time_off_employee.name} - {period.name}',
                'employee_id': time_off_employee.id,
                'contract_id': time_off_contract.id,
                'struct_id': self.structure.id,
                'date_from': period.date_start,
                'date_to': period.date_end,
                'company_id': self.company.id,
            })
            
            payslip.compute_sheet()
            payslip.action_payslip_done()
        
        # Create provision calculation
        provision = self.env['hr.provision.calculation'].create({
            'name': 'Cálculo de Provisiones con Ausencias',
            'date_from': date.today() - relativedelta(months=6),
            'date_to': date.today(),
            'provision_type': 'all',
            'company_id': self.company.id,
        })
        
        # Load employees
        provision.action_load_employees()
        
        # Check that time off employee was loaded
        time_off_line = provision.line_ids.filtered(lambda l: l.employee_id == time_off_employee)
        self.assertTrue(time_off_line, "Time off employee not loaded")
        
        # Calculate provisions
        provision.action_calculate()
        
        # Check that worked days were adjusted for unpaid leave
        # 6 months = 180 days, minus 10 days unpaid leave = 170 days
        self.assertEqual(time_off_line.worked_days, 170, "Worked days not adjusted for unpaid leave")
        
        # Check severance calculation with adjusted worked days
        expected_base = time_off_line.wage + time_off_line.transport_allowance
        expected_severance = expected_base * time_off_line.worked_days / 360
        self.assertAlmostEqual(time_off_line.severance_value, expected_severance, delta=1.0)
        self.assertAlmostEqual(time_off_line.severance_value, expected_severance, delta=1.0, 
                              msg="Wrong severance calculation with time off")

    def test_11_provision_report(self):
        """Test provision report generation."""
        provision = self.env['hr.provision.calculation'].create({
            'name': 'Cálculo de Provisiones para Reporte',
            'date_from': date.today().replace(day=1) - relativedelta(months=1),
            'date_to': date.today().replace(day=1) - relativedelta(days=1),
            'provision_type': 'all',
            'company_id': self.company.id,
        })
        
        # Load employees and calculate
        provision.action_load_employees()
        provision.action_calculate()
        
        # Generate report
        report_action = provision.print_report()
        
        # Check report action
        self.assertTrue(report_action, "Report action should be returned")
        self.assertEqual(report_action.get('type'), 'ir.actions.report', "Action should be a report")
        
        # Generate detailed report
        detailed_action = provision.print_detailed_report()
        
        # Check detailed report action
        self.assertTrue(detailed_action, "Detailed report action should be returned")
        self.assertEqual(detailed_action.get('type'), 'ir.actions.report', "Action should be a report")

    def test_12_export_provision_to_excel(self):
        """Test exporting provision data to Excel."""
        provision = self.env['hr.provision.calculation'].create({
            'name': 'Cálculo de Provisiones para Excel',
            'date_from': date.today().replace(day=1) - relativedelta(months=1),
            'date_to': date.today().replace(day=1) - relativedelta(days=1),
            'provision_type': 'all',
            'company_id': self.company.id,
        })
        
        # Load employees and calculate
        provision.action_load_employees()
        provision.action_calculate()
        
        # Export to Excel
        export_action = provision.action_export_excel()
        
        # Check export action
        self.assertTrue(export_action, "Export action should be returned")
        self.assertEqual(export_action.get('type'), 'ir.actions.act_url', "Action should be URL action")
        self.assertTrue(export_action.get('url'), "URL should be provided")
        self.assertTrue('xlsx' in export_action.get('url', ''), "URL should point to Excel file")

    def test_13_provision_workflow(self):
        """Test complete provision workflow."""
        provision = self.env['hr.provision.calculation'].create({
            'name': 'Cálculo de Provisiones Workflow',
            'date_from': date.today().replace(day=1) - relativedelta(months=1),
            'date_to': date.today().replace(day=1) - relativedelta(days=1),
            'provision_type': 'all',
            'company_id': self.company.id,
        })
        
        # Initial state should be draft
        self.assertEqual(provision.state, 'draft', "Initial state should be draft")
        
        # Load employees
        provision.action_load_employees()
        self.assertTrue(provision.line_ids, "Employees should be loaded")
        
        # Calculate provisions
        provision.action_calculate()
        self.assertEqual(provision.state, 'calculated', "State should be calculated")
        
        # Validate provision
        provision.action_validate()
        self.assertEqual(provision.state, 'validated', "State should be validated")
        
        # Confirm provision
        provision.action_confirm()
        self.assertEqual(provision.state, 'confirmed', "State should be confirmed")
        
        # Test reset to draft
        provision.action_reset_draft()
        self.assertEqual(provision.state, 'draft', "State should be reset to draft")
        
        # Test cancellation
        provision.action_cancel()
        self.assertEqual(provision.state, 'cancelled', "State should be cancelled")

    def test_14_provision_accounting_entries(self):
        """Test generation of accounting entries for provisions."""
        # Create provision calculation
        provision = self.env['hr.provision.calculation'].create({
            'name': 'Cálculo de Provisiones Contables',
            'date_from': date.today().replace(day=1) - relativedelta(months=1),
            'date_to': date.today().replace(day=1) - relativedelta(days=1),
            'provision_type': 'all',
            'company_id': self.company.id,
        })
        
        # Load employees and calculate
        provision.action_load_employees()
        provision.action_calculate()
        
        # Validate provision
        provision.action_validate()
        
        # Generate accounting entries
        provision.action_create_accounting_entries()
        
        # Check that accounting entry was created
        self.assertTrue(provision.move_id, "Accounting entry not created")
        self.assertEqual(provision.move_id.state, 'draft', "Accounting entry should be in draft state")
        
        # Check move lines
        self.assertTrue(provision.move_id.line_ids, "Move lines not created")
        
        # Should have at least 8 move lines (4 debits and 4 credits for each provision type)
        self.assertTrue(len(provision.move_id.line_ids) >= 8, "Not enough move lines created")
        
        # Check that total debit equals total credit
        total_debit = sum(provision.move_id.line_ids.mapped('debit'))
        total_credit = sum(provision.move_id.line_ids.mapped('credit'))
        self.assertAlmostEqual(total_debit, total_credit, delta=0.01, 
                              msg="Total debit should equal total credit")
        
        # Check that total amount matches provision total
        self.assertAlmostEqual(total_debit, provision.total_provision, delta=0.01, 
                              msg="Total debit should match provision total")

    def test_15_provision_with_partial_period(self):
        """Test provisions calculation for a partial period."""
        # Create provision for just 15 days
        start_date = date.today() - relativedelta(days=15)
        end_date = date.today()
        
        provision = self.env['hr.provision.calculation'].create({
            'name': 'Cálculo de Provisiones Periodo Parcial',
            'date_from': start_date,
            'date_to': end_date,
            'provision_type': 'all',
            'company_id': self.company.id,
        })
        
        # Load employees
        provision.action_load_employees()
        
        # Calculate provisions
        provision.action_calculate()
        
        # Check that provisions were calculated proportionally
        employee1_line = provision.line_ids.filtered(lambda l: l.employee_id == self.employee1)
        
        # For a 15-day period, worked days should be 15
        self.assertEqual(employee1_line.period_days, 15, "Period days should be 15")
        
        # Severance should be proportional to 15 days
        expected_base = employee1_line.wage + employee1_line.transport_allowance
        expected_severance = expected_base * 15 / 360
        self.assertAlmostEqual(employee1_line.severance_value, expected_severance, delta=1.0, 
                              msg="Wrong severance calculation for partial period")

    def test_16_provision_with_multiple_contracts(self):
        """Test provisions calculation for an employee with multiple contracts."""
        # Create employee with multiple contracts
        multi_contract_employee = self.env['hr.employee'].create({
            'name': 'Empleado Multi Contrato',
            'identification_id': '1357924680',
            'gender': 'male',
            'birthday': '1990-06-15',
            'country_id': self.env.ref('base.co').id,
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
        
        # Create first contract (ended 3 months ago)
        first_contract = self.env['hr.contract'].create({
            'name': 'Primer Contrato',
            'employee_id': multi_contract_employee.id,
            'job_id': self.job.id,
            'type_id': self.contract_type_fixed.id,
            'wage': 1600000.0,
            'state': 'close',  # Contract ended
            'date_start': date.today() - relativedelta(months=6),
            'date_end': date.today() - relativedelta(months=3),
            'structure_type_id': self.structure_type.id,
            'resource_calendar_id': self.env.ref('resource.resource_calendar_std').id,
            'company_id': self.company.id,
            'transport_allowance': True,
        })
        
        # Create second contract (started 3 months ago)
        second_contract = self.env['hr.contract'].create({
            'name': 'Segundo Contrato',
            'employee_id': multi_contract_employee.id,
            'job_id': self.job.id,
            'type_id': self.contract_type_indefinite.id,
            'wage': 1800000.0,
            'state': 'open',
            'date_start': date.today() - relativedelta(months=3),
            'structure_type_id': self.structure_type.id,
            'resource_calendar_id': self.env.ref('resource.resource_calendar_std').id,
            'company_id': self.company.id,
            'transport_allowance': True,
        })
        
        # Create payslips for both contracts
        # First contract payslips
        for i in range(3):
            period = self.periods[-6+i] if i < len(self.periods) else self.current_period
            payslip = self.env['hr.payslip'].create({
                'name': f'Nómina Primer Contrato - {period.name}',
                'employee_id': multi_contract_employee.id,
                'contract_id': first_contract.id,
                'struct_id': self.structure.id,
                'date_from': period.date_start,
                'date_to': period.date_end,
                'company_id': self.company.id,
            })
            payslip.compute_sheet()
            payslip.action_payslip_done()
        
        # Second contract payslips
        for i in range(3):
            period = self.periods[-3+i] if i < len(self.periods) else self.current_period
            payslip = self.env['hr.payslip'].create({
                'name': f'Nómina Segundo Contrato - {period.name}',
                'employee_id': multi_contract_employee.id,
                'contract_id': second_contract.id,
                'struct_id': self.structure.id,
                'date_from': period.date_start,
                'date_to': period.date_end,
                'company_id': self.company.id,
            })
            payslip.compute_sheet()
            payslip.action_payslip_done()
        
        # Create provision calculation
        provision = self.env['hr.provision.calculation'].create({
            'name': 'Cálculo de Provisiones Multi Contrato',
            'date_from': date.today() - relativedelta(months=6),
            'date_to': date.today(),
            'provision_type': 'all',
            'company_id': self.company.id,
        })
        
        # Load employees
        provision.action_load_employees()
        
        # Check that employee with multiple contracts was loaded
        multi_contract_lines = provision.line_ids.filtered(lambda l: l.employee_id == multi_contract_employee)
        
        # Should have two lines, one for each contract
        self.assertEqual(len(multi_contract_lines), 2, "Should have two lines for employee with multiple contracts")
        
        # Calculate provisions
        provision.action_calculate()
        
        # Check that provisions were calculated correctly for each contract
        first_contract_line = provision.line_ids.filtered(lambda l: l.contract_id == first_contract)
        second_contract_line = provision.line_ids.filtered(lambda l: l.contract_id == second_contract)
        
        # First contract should have worked days for 3 months (90 days)
        self.assertEqual(first_contract_line.worked_days, 90, "First contract should have 90 worked days")
        
        # Second contract should have worked days for 3 months (90 days)
        self.assertEqual(second_contract_line.worked_days, 90, "Second contract should have 90 worked days")
        
        # Check severance calculations for each contract
        expected_base1 = first_contract_line.wage + first_contract_line.transport_allowance
        expected_severance1 = expected_base1 * 90 / 360
        self.assertAlmostEqual(first_contract_line.severance_value, expected_severance1, delta=1.0, 
                              msg="Wrong severance calculation for first contract")
        
        expected_base2 = second_contract_line.wage + second_contract_line.transport_allowance
        expected_severance2 = expected_base2 * 90 / 360
        self.assertAlmostEqual(second_contract_line.severance_value, expected_severance2, delta=1.0, 
                              msg="Wrong severance calculation for second contract")

    def test_17_provision_consolidation(self):
        """Test consolidation of provisions for reporting."""
        # Create multiple provision calculations
        provision1 = self.env['hr.provision.calculation'].create({
            'name': 'Provisiones Enero',
            'date_from': date.today().replace(month=1, day=1),
            'date_to': date.today().replace(month=1, day=31),
            'provision_type': 'all',
            'company_id': self.company.id,
        })
        
        provision2 = self.env['hr.provision.calculation'].create({
            'name': 'Provisiones Febrero',
            'date_from': date.today().replace(month=2, day=1),
            'date_to': date.today().replace(month=2, day=28),
            'provision_type': 'all',
            'company_id': self.company.id,
        })
        
        # Load employees and calculate
        provision1.action_load_employees()
        provision1.action_calculate()
        provision1.action_validate()
        provision1.action_confirm()
        
        provision2.action_load_employees()
        provision2.action_calculate()
        provision2.action_validate()
        provision2.action_confirm()
        
        # Create consolidation wizard
        wizard = self.env['hr.provision.consolidation.wizard'].create({
            'date_from': date.today().replace(month=1, day=1),
            'date_to': date.today().replace(month=2, day=28),
            'company_id': self.company.id,
        })
        
        # Generate consolidation report
        result = wizard.generate_report()
        
        # Check if report was generated
        self.assertTrue(result, "Consolidation report was not generated")
        self.assertEqual(result.get('type'), 'ir.actions.report', 
                         "Action returned is not a report")
        
        # Check consolidated data
        consolidated_data = self.env['hr.provision.consolidation'].search([
            ('date_from', '=', date.today().replace(month=1, day=1)),
            ('date_to', '=', date.today().replace(month=2, day=28)),
        ], limit=1)
        
        self.assertTrue(consolidated_data, "Consolidated data was not created")
        self.assertTrue(consolidated_data.line_ids, "Consolidated lines were not created")
        
        # Total should be sum of both provisions
        expected_total = provision1.total_provision + provision2.total_provision
        self.assertAlmostEqual(consolidated_data.total_provision, expected_total, delta=1.0, 
                              msg="Wrong total in consolidated report")

    def test_18_provision_adjustment(self):
        """Test adjustment of provisions."""
        # Create provision calculation
        provision = self.env['hr.provision.calculation'].create({
            'name': 'Provisiones para Ajuste',
            'date_from': date.today().replace(day=1) - relativedelta(months=1),
            'date_to': date.today().replace(day=1) - relativedelta(days=1),
            'provision_type': 'all',
            'company_id': self.company.id,
        })
        
        # Load employees and calculate
        provision.action_load_employees()
        provision.action_calculate()
        
        # Get a line to adjust
        line = provision.line_ids[0]
        original_severance = line.severance_value
        original_prima = line.prima_value
        
        # Create adjustment wizard
        wizard = self.env['hr.provision.adjustment.wizard'].create({
            'provision_id': provision.id,
            'line_id': line.id,
            'severance_adjustment': 50000.0,
            'prima_adjustment': -20000.0,
            'notes': 'Ajuste manual de prueba',
        })
        
        # Apply adjustment
        wizard.apply_adjustment()
        
        # Check that adjustments were applied
        self.assertAlmostEqual(line.severance_value, original_severance + 50000.0, delta=0.01, 
                              msg="Severance adjustment not applied")
        self.assertAlmostEqual(line.prima_value, original_prima - 20000.0, delta=0.01, 
                              msg="Prima adjustment not applied")
        
        # Check that adjustment was recorded
        self.assertTrue(line.adjustment_ids, "Adjustment record not created")
        adjustment = line.adjustment_ids[0]
        self.assertEqual(adjustment.severance_adjustment, 50000.0, "Wrong severance adjustment value")
        self.assertEqual(adjustment.prima_adjustment, -20000.0, "Wrong prima adjustment value")
        self.assertEqual(adjustment.notes, 'Ajuste manual de prueba', "Wrong adjustment notes")

    def test_19_provision_payment(self):
        """Test payment of provisions."""
        # Create provision calculation
        provision = self.env['hr.provision.calculation'].create({
            'name': 'Provisiones para Pago',
            'date_from': date.today().replace(month=1, day=1),
            'date_to': date.today().replace(month=6, day=30),
            'provision_type': 'all',
            'company_id': self.company.id,
        })
        
        # Load employees and calculate
        provision.action_load_employees()
        provision.action_calculate()
        provision.action_validate()
        provision.action_confirm()
        
        # Create payment wizard for prima (paid in June)
        payment_wizard = self.env['hr.provision.payment.wizard'].create({
            'name': 'Pago de Prima Semestral',
            'date': date.today().replace(month=6, day=30),
            'provision_type': 'prima',
            'company_id': self.company.id,
        })
        
        # Load provisions
        payment_wizard.action_load_provisions()
        
        # Check that provisions were loaded
        self.assertTrue(payment_wizard.line_ids, "Payment lines were not created")
        
        # Generate payment
        result = payment_wizard.generate_payment()
        
        # Check if payment was generated
        self.assertTrue(result, "Payment was not generated")
        
        # Check payment record
        payment = self.env['hr.provision.payment'].search([
            ('name', '=', 'Pago de Prima Semestral'),
            ('date', '=', date.today().replace(month=6, day=30)),
        ], limit=1)
        
        self.assertTrue(payment, "Payment record was not created")
        self.assertTrue(payment.line_ids, "Payment lines were not created")
        self.assertEqual(payment.provision_type, 'prima', "Wrong provision type")
        self.assertEqual(payment.state, 'draft', "Payment should be in draft state")
        
        # Confirm payment
        payment.action_confirm()
        self.assertEqual(payment.state, 'confirmed', "Payment should be in confirmed state")
        
        # Check that accounting entry was created
        self.assertTrue(payment.move_id, "Accounting entry not created for payment")
        
        # Create new provision calculation after payment
        new_provision = self.env['hr.provision.calculation'].create({
            'name': 'Provisiones Post-Pago',
            'date_from': date.today().replace(month=7, day=1),
            'date_to': date.today().replace(month=7, day=31),
            'provision_type': 'all',
            'company_id': self.company.id,
        })
        
        # Load employees and calculate
        new_provision.action_load_employees()
        new_provision.action_calculate()
        
        # Check that prima provision was reset after payment
        employee1_line = new_provision.line_ids.filtered(lambda l: l.employee_id == self.employee1)
        self.assertTrue(employee1_line, "Employee 1 line not found in new provision")
        
        # Prima should be calculated only for July (1 month)
        expected_base = employee1_line.wage + employee1_line.transport_allowance
        expected_prima = expected_base * 30 / 360  # 30 days / 360
        self.assertAlmostEqual(employee1_line.prima_value, expected_prima, delta=1000.0, 
                              msg="Prima not reset after payment")

    def test_20_provision_validation_rules(self):
        """Test provision validation rules."""
        # Create provision with invalid dates (end date before start date)
        with self.assertRaises(ValidationError):
            self.env['hr.provision.calculation'].create({
                'name': 'Provisiones Fechas Inválidas',
                'date_from': date.today(),
                'date_to': date.today() - relativedelta(days=1),
                'provision_type': 'all',
                'company_id': self.company.id,
            })
        
        # Create provision with valid dates
        provision = self.env['hr.provision.calculation'].create({
            'name': 'Provisiones para Validación',
            'date_from': date.today().replace(day=1) - relativedelta(months=1),
            'date_to': date.today().replace(day=1) - relativedelta(days=1),
            'provision_type': 'all',
            'company_id': self.company.id,
        })
        
        # Load employees
        provision.action_load_employees()
        
        # Try to validate without calculating first
        with self.assertRaises(UserError):
            provision.action_validate()
        
        # Calculate provisions
        provision.action_calculate()
        
        # Now validation should work
        provision.action_validate()
        self.assertEqual(provision.state, 'validated', "Provision should be in validated state")
        
        # Try to modify a validated provision
        with self.assertRaises(UserError):
            provision.write({'name': 'New Name'})
        
        # Reset to draft
        provision.action_reset_draft()
        
        # Now modification should work
        provision.write({'name': 'New Name'})
        self.assertEqual(provision.name, 'New Name', "Provision name not updated")