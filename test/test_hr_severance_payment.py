from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

@tagged('post_install', '-at_install', 'severance')
class TestHrSeverancePayment(TransactionCase):
    """Test cases for Colombian severance payment calculations."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test company with Colombian localization
        cls.company = cls.env['res.company'].create({
            'name': 'Colombian Test Company',
            'country_id': cls.env.ref('base.co').id,
        })
        
        # Set company for current user
        cls.env.user.company_id = cls.company
        
        # Create employee category
        cls.category = cls.env['hr.employee.category'].create({
            'name': 'Test Category',
        })
        
        # Create department
        cls.department = cls.env['hr.department'].create({
            'name': 'Test Department',
            'company_id': cls.company.id,
        })
        
        # Create job position
        cls.job = cls.env['hr.job'].create({
            'name': 'Test Job',
            'company_id': cls.company.id,
        })
        
        # Create employee
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'identification_id': '1234567890',
            'gender': 'male',
            'birthday': '1990-01-01',
            'country_id': cls.env.ref('base.co').id,
            'department_id': cls.department.id,
            'job_id': cls.job.id,
            'category_ids': [(4, cls.category.id)],
            'company_id': cls.company.id,
        })
        
        # Create contract type
        cls.contract_type = cls.env['hr.contract.type'].create({
            'name': 'Test Contract Type',
        })
        
        # Create structure type (new in v18)
        cls.structure_type = cls.env['hr.payroll.structure.type'].create({
            'name': 'Test Structure Type',
            'country_id': cls.env.ref('base.co').id,
        })
        
        # Create payroll structure
        cls.structure = cls.env['hr.payroll.structure'].create({
            'name': 'Colombian Test Structure',
            'type_id': cls.structure_type.id,
            'country_id': cls.env.ref('base.co').id,
            'company_id': cls.company.id,
        })
        
        # Create work entry type (new in v18)
        cls.work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'Test Work Entry Type',
            'code': 'TEST',
            'is_leave': False,
        })
        
        # Create contract
        today = date.today()
        cls.contract_start = today - relativedelta(years=1, months=2)
        cls.contract = cls.env['hr.contract'].create({
            'name': 'Test Contract',
            'employee_id': cls.employee.id,
            'department_id': cls.department.id,
            'job_id': cls.job.id,
            'type_id': cls.contract_type.id,
            'wage': 1500000.0,  # 1.5 million COP
            'state': 'open',
            'date_start': cls.contract_start,
            'resource_calendar_id': cls.env.ref('resource.resource_calendar_std').id,
            'structure_type_id': cls.structure_type.id,
            'company_id': cls.company.id,
        })
        
        # Create salary rules for severance
        cls.category_severance = cls.env['hr.salary.rule.category'].create({
            'name': 'Cesantías',
            'code': 'CESANTIAS',
        })
        
        cls.rule_severance = cls.env['hr.salary.rule'].create({
            'name': 'Cesantías',
            'code': 'CESANTIAS',
            'category_id': cls.category_severance.id,
            'sequence': 110,
            'condition_select': 'none',
            'amount_select': 'code',
            'amount_python_compute': """
result = contract.wage * worked_days.WORK100.number_of_days / 30
if contract.wage <= payslip.company_id.severance_base_salary * 2:
    result += transportation_allowance * worked_days.WORK100.number_of_days / 30
""",
            'struct_id': cls.structure.id,
        })
        
        # Create severance fund
        cls.severance_fund = cls.env['res.partner'].create({
            'name': 'Test Severance Fund',
            'company_type': 'company',
            'country_id': cls.env.ref('base.co').id,
        })
        
        # Update employee with severance fund
        cls.employee.write({
            'severance_fund_id': cls.severance_fund.id,
        })

    def test_01_calculate_severance_payment(self):
        """Test the calculation of severance payment for a full year."""
        # Create a severance payment calculation wizard
        wizard = self.env['hr.severance.payment.wizard'].create({
            'employee_id': self.employee.id,
            'calculation_date': date.today(),
        })
        
        # Calculate severance
        wizard.calculate_severance()
        
        # Check the calculated amount (basic test)
        self.assertTrue(wizard.amount > 0, "Severance amount should be greater than zero")
        
        # More detailed calculation check
        expected_amount = self.contract.wage * (date.today() - self.contract_start).days / 360
        self.assertAlmostEqual(
            wizard.amount, 
            expected_amount, 
            delta=1.0,  # Allow for rounding differences
            msg="Severance calculation doesn't match expected amount"
        )

    def test_02_severance_with_salary_changes(self):
        """Test severance calculation with salary changes during the period."""
        # Create salary history
        six_months_ago = date.today() - relativedelta(months=6)
        
        # Update contract with salary history
        self.contract.write({
            'wage_history_ids': [(0, 0, {
                'wage': 1200000.0,  # Previous salary
                'date_start': self.contract_start,
                'date_end': six_months_ago - timedelta(days=1),
            }), (0, 0, {
                'wage': 1500000.0,  # Current salary
                'date_start': six_months_ago,
                'date_end': False,
            })],
        })
        
        # Create a severance payment calculation wizard
        wizard = self.env['hr.severance.payment.wizard'].create({
            'employee_id': self.employee.id,
            'calculation_date': date.today(),
        })
        
        # Calculate severance
        wizard.calculate_severance()
        
        # Calculate expected amount with weighted average
        first_period = (six_months_ago - self.contract_start).days
        second_period = (date.today() - six_months_ago).days
        total_days = first_period + second_period
        
        weighted_salary = (1200000.0 * first_period + 1500000.0 * second_period) / total_days
        expected_amount = weighted_salary * total_days / 360
        
        self.assertAlmostEqual(
            wizard.amount, 
            expected_amount, 
            delta=1.0,
            msg="Severance calculation with salary changes doesn't match expected amount"
        )

    def test_03_partial_year_severance(self):
        """Test severance calculation for partial year."""
        # Create a contract with start date 3 months ago
        three_months_ago = date.today() - relativedelta(months=3)
        
        short_contract = self.env['hr.contract'].create({
            'name': 'Short Test Contract',
            'employee_id': self.employee.id,
            'department_id': self.department.id,
            'job_id': cls.job.id,
            'type_id': self.contract_type.id,
            'wage': 1500000.0,
            'state': 'open',
            'date_start': three_months_ago,
            'resource_calendar_id': self.env.ref('resource.resource_calendar_std').id,
            'structure_type_id': self.structure_type.id,
            'company_id': self.company.id,
        })
        
        # Set this as active contract
        self.contract.state = 'close'
        short_contract.state = 'open'
        
        # Create a severance payment calculation wizard
        wizard = self.env['hr.severance.payment.wizard'].create({
            'employee_id': self.employee.id,
            'calculation_date': date.today(),
        })
        
        # Calculate severance
        wizard.calculate_severance()
        
        # Check the calculated amount for partial year
        days_worked = (date.today() - three_months_ago).days
        expected_amount = short_contract.wage * days_worked / 360
        
        self.assertAlmostEqual(
            wizard.amount, 
            expected_amount, 
            delta=1.0,
            msg="Partial year severance calculation doesn't match expected amount"
        )

    def test_04_generate_severance_payment(self):
        """Test the generation of severance payment entry."""
        # Create a severance payment calculation wizard
        wizard = self.env['hr.severance.payment.wizard'].create({
            'employee_id': self.employee.id,
            'calculation_date': date.today(),
            'payment_date': date.today(),
            'journal_id': self.env['account.journal'].search([('type', '=', 'general')], limit=1).id,
        })
        
        # Calculate severance
        wizard.calculate_severance()
        
        # Generate payment
        payment = wizard.generate_payment()
        
        # Check that payment was created
        self.assertTrue(payment, "Severance payment should be created")
        self.assertEqual(payment.employee_id, self.employee, "Payment should be linked to the correct employee")
        self.assertAlmostEqual(
            payment.amount, 
            wizard.amount, 
            places=2,
            msg="Payment amount should match the calculated amount"
        )

    def test_05_severance_interest(self):
        """Test the calculation of interest on severance."""
        # Create a severance interest calculation wizard
        wizard = self.env['hr.severance.interest.wizard'].create({
            'employee_id': self.employee.id,
            'year': date.today().year - 1,  # Previous year
        })
        
        # Calculate interest
        wizard.calculate_interest()
        
        # Check the calculated interest
        self.assertTrue(wizard.interest_amount > 0, "Interest amount should be greater than zero")
        
        # More detailed calculation check (12% annual interest)
        expected_interest = self.contract.wage * 12 * 0.12
        self.assertAlmostEqual(
            wizard.interest_amount, 
            expected_interest, 
            delta=100.0,  # Allow for calculation differences
            msg="Interest calculation doesn't match expected amount"
        )

    @freeze_time('2023-12-31')
    def test_06_end_of_year_severance_transfer(self):
        """Test the end of year severance transfer to fund."""
        # Create a severance transfer wizard
        wizard = self.env['hr.severance.transfer.wizard'].create({
            'year': 2023,
            'transfer_date': date(2023, 12, 31),
            'fund_id': self.severance_fund.id,
        })
        
        # Calculate transfers
        wizard.calculate_transfers()
        
        # Check that the employee is in the transfer lines
        employee_line = wizard.line_ids.filtered(lambda l: l.employee_id == self.employee)
        self.assertTrue(employee_line, "Employee should be included in transfer lines")
        
        # Process the transfer
        wizard.process_transfer()
        
        # Check that transfer record was created
        transfer = self.env['hr.severance.transfer'].search([
            ('employee_id', '=', self.employee.id),
            ('year', '=', 2023)
        ])
        self.assertTrue(transfer, "Severance transfer record should be created")
        self.assertEqual(transfer.state, 'done', "Transfer should be in 'done' state")
    
    def test_07_severance_with_transportation_allowance(self):
        """Test severance calculation including transportation allowance."""
        # Set company transportation allowance
        self.company.write({
            'transportation_allowance': 140606.0,  # 2023 Colombian transportation allowance
            'severance_base_salary': 1160000.0,  # 2023 Colombian minimum wage
        })
        
        # Update contract to be eligible for transportation allowance
        self.contract.write({
            'wage': 1800000.0,  # Below 2x minimum wage
            'transportation_allowance': True,
        })
        
        # Create a severance payment calculation wizard
        wizard = self.env['hr.severance.payment.wizard'].create({
            'employee_id': self.employee.id,
            'calculation_date': date.today(),
        })
        
        # Calculate severance
        wizard.calculate_severance()
        
        # Calculate expected amount including transportation allowance
        days_worked = (date.today() - self.contract_start).days
        expected_amount = (self.contract.wage + 140606.0) * days_worked / 360
        
        self.assertAlmostEqual(
            wizard.amount, 
            expected_amount, 
            delta=1.0,
            msg="Severance calculation with transportation allowance doesn't match expected amount"
        )

    def test_08_severance_withdrawal_request(self):
        """Test the severance partial withdrawal request process."""
        # Create a severance withdrawal request
        withdrawal = self.env['hr.severance.withdrawal'].create({
            'employee_id': self.employee.id,
            'request_date': date.today(),
            'amount': 1000000.0,
            'reason': 'housing',  # Valid reason for partial withdrawal
            'description': 'Home improvement',
        })
        
        # Submit the request
        withdrawal.action_submit()
        self.assertEqual(withdrawal.state, 'submitted', "Withdrawal request should be in 'submitted' state")
        
        # Approve the request
        withdrawal.action_approve()
        self.assertEqual(withdrawal.state, 'approved', "Withdrawal request should be in 'approved' state")
        
        # Process the payment
        withdrawal.action_process()
        self.assertEqual(withdrawal.state, 'done', "Withdrawal request should be in 'done' state")
        
        # Check that payment record was created
        self.assertTrue(withdrawal.payment_id, "Payment record should be created")
        self.assertEqual(withdrawal.payment_id.state, 'posted', "Payment should be posted")

    def test_09_severance_consolidation_report(self):
        """Test the generation of severance consolidation report."""
        # Create several employees with contracts
        employees = self.employee
        for i in range(2):
            emp = self.env['hr.employee'].create({
                'name': f'Test Employee {i+2}',
                'identification_id': f'123456789{i}',
                'gender': 'female',
                'birthday': '1992-01-01',
                'country_id': self.env.ref('base.co').id,
                'department_id': self.department.id,
                'job_id': self.job.id,
                'category_ids': [(4, self.category.id)],
                'company_id': self.company.id,
                'severance_fund_id': self.severance_fund.id,
            })
            
            # Create contract
            start_date = date.today() - relativedelta(months=i+6)
            self.env['hr.contract'].create({
                'name': f'Test Contract {i+2}',
                'employee_id': emp.id,
                'department_id': self.department.id,
                'job_id': self.job.id,
                'type_id': self.contract_type.id,
                'wage': 1500000.0 + (i * 200000.0),
                'state': 'open',
                'date_start': start_date,
                'resource_calendar_id': self.env.ref('resource.resource_calendar_std').id,
                'structure_type_id': self.structure_type.id,
                'company_id': self.company.id,
            })
        
        # Create a consolidation report wizard
        wizard = self.env['hr.severance.consolidation.wizard'].create({
            'date': date.today(),
            'fund_id': self.severance_fund.id,
        })
        
        # Generate report
        report = wizard.generate_report()
        
        # Check report data
        self.assertTrue(report, "Report should be generated")
        self.assertTrue(len(report.line_ids) >= 3, "Report should include at least 3 employees")
        
        # Check totals
        self.assertTrue(report.total_amount > 0, "Total amount should be greater than zero")
        self.assertEqual(
            sum(report.line_ids.mapped('amount')), 
            report.total_amount,
            "Sum of line amounts should equal total amount"
        )

    def test_10_severance_with_contract_termination(self):
        """Test severance calculation with contract termination."""
        # Set contract end date
        termination_date = date.today() - timedelta(days=15)
        self.contract.write({
            'date_end': termination_date,
            'state': 'close',
        })
        
        # Create termination record
        termination = self.env['hr.contract.termination'].create({
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'termination_date': termination_date,
            'termination_type': 'voluntary',
            'notice_respected': True,
        })
        
        # Process termination
        termination.action_validate()
        
        # Create a severance payment calculation wizard
        wizard = self.env['hr.severance.payment.wizard'].create({
            'employee_id': self.employee.id,
            'calculation_date': termination_date,
            'termination_id': termination.id,
        })
        
        # Calculate severance
        wizard.calculate_severance()
        
        # Check the calculated amount for terminated contract
        days_worked = (termination_date - self.contract_start).days
        expected_amount = self.contract.wage * days_worked / 360
        
        self.assertAlmostEqual(
            wizard.amount, 
            expected_amount, 
            delta=1.0,
            msg="Severance calculation for terminated contract doesn't match expected amount"
        )
        
        # Generate payment
        payment = wizard.generate_payment()
        
        # Check payment is linked to termination
        self.assertEqual(
            payment.termination_id, 
            termination,
            "Payment should be linked to termination record"
        )

    def test_11_retroactive_salary_adjustment(self):
        """Test severance recalculation after retroactive salary adjustment."""
        # Create initial severance calculation
        initial_wizard = self.env['hr.severance.payment.wizard'].create({
            'employee_id': self.employee.id,
            'calculation_date': date.today(),
        })
        initial_wizard.calculate_severance()
        initial_amount = initial_wizard.amount
        
        # Apply retroactive salary adjustment
        adjustment_date = date.today() - relativedelta(months=3)
        self.env['hr.contract.wage.adjustment'].create({
            'contract_id': self.contract.id,
            'adjustment_date': adjustment_date,
            'previous_wage': self.contract.wage,
            'new_wage': self.contract.wage * 1.1,  # 10% increase
            'retroactive': True,
            'retroactive_from': self.contract_start,
        })
        
        # Recalculate severance
        recalc_wizard = self.env['hr.severance.payment.wizard'].create({
            'employee_id': self.employee.id,
            'calculation_date': date.today(),
            'include_retroactive': True,
        })
        recalc_wizard.calculate_severance()
        
        # Check that amount increased
        self.assertTrue(
            recalc_wizard.amount > initial_amount,
            "Severance amount should increase after retroactive salary adjustment"
        )
        
        # Check retroactive component
        self.assertTrue(
            recalc_wizard.retroactive_amount > 0,
            "Retroactive amount should be greater than zero"
        )

    def test_12_severance_interest_payment(self):
        """Test the generation of severance interest payment."""
        # Create a severance interest calculation wizard
        wizard = self.env['hr.severance.interest.wizard'].create({
            'employee_id': self.employee.id,
            'year': date.today().year - 1,  # Previous year
            'payment_date': date.today(),
            'journal_id': self.env['account.journal'].search([('type', '=', 'general')], limit=1).id,
        })
        
        # Calculate interest
        wizard.calculate_interest()
        
        # Generate payment
        payment = wizard.generate_payment()
        
        # Check that payment was created
        self.assertTrue(payment, "Interest payment should be created")
        self.assertEqual(payment.employee_id, self.employee, "Payment should be linked to the correct employee")
        self.assertEqual(payment.payment_type, 'interest', "Payment type should be 'interest'")
        self.assertAlmostEqual(
            payment.amount, 
            wizard.interest_amount, 
            places=2,
            msg="Payment amount should match the calculated interest amount"
        )
        
        # Check accounting entries
        self.assertTrue(payment.move_id, "Accounting entry should be created")
        self.assertEqual(payment.move_id.state, 'posted', "Accounting entry should be posted")

    def test_13_mass_severance_transfer(self):
        """Test mass severance transfer to funds."""
        # Create several employees with different funds
        fund2 = self.env['res.partner'].create({
            'name': 'Second Severance Fund',
            'company_type': 'company',
            'country_id': self.env.ref('base.co').id,
        })
        
        employees = []
        for i in range(4):
            fund = self.severance_fund if i % 2 == 0 else fund2
            emp = self.env['hr.employee'].create({
                'name': f'Mass Transfer Employee {i+1}',
                'identification_id': f'9876543{i}',
                'gender': 'male' if i % 2 == 0 else 'female',
                'country_id': self.env.ref('base.co').id,
                'department_id': self.department.id,
                'company_id': self.company.id,
                'severance_fund_id': fund.id,
            })
            employees.append(emp)
            
            # Create contract
            self.env['hr.contract'].create({
                'name': f'Mass Transfer Contract {i+1}',
                'employee_id': emp.id,
                'department_id': self.department.id,
                'job_id': self.job.id,
                'type_id': self.contract_type.id,
                'wage': 1000000.0 + (i * 100000.0),
                'state': 'open',
                'date_start': date.today() - relativedelta(months=i+3),
                'resource_calendar_id': self.env.ref('resource.resource_calendar_std').id,
                'structure_type_id': self.structure_type.id,
                'company_id': self.company.id,
            })
        
        # Create mass transfer wizard
        wizard = self.env['hr.severance.mass.transfer.wizard'].create({
            'calculation_date': date.today(),
            'transfer_date': date.today(),
        })
        
        # Calculate transfers
        wizard.calculate_transfers()
        
        # Check that lines were created for all employees
        self.assertEqual(
            len(wizard.line_ids), 
            len(employees) + 1,  # +1 for the original employee
            "Should have transfer lines for all employees"
        )
        
        # Check grouping by fund
        self.assertEqual(
            len(wizard.fund_ids), 
            2,
            "Should have two different funds"
        )
        
        # Process transfers
        wizard.process_transfers()
        
        # Check that transfer records were created
        transfers = self.env['hr.severance.transfer'].search([
            ('employee_id', 'in', [e.id for e in employees] + [self.employee.id]),
            ('transfer_date', '=', date.today())
        ])
        self.assertEqual(
            len(transfers), 
            len(employees) + 1,
            "Should have transfer records for all employees"
        )

    def test_14_severance_with_variable_salary(self):
        """Test severance calculation with variable salary components."""
        # Create variable salary rule
        variable_category = self.env['hr.salary.rule.category'].create({
            'name': 'Variable',
            'code': 'VAR',
        })
        
        variable_rule = self.env['hr.salary.rule'].create({
            'name': 'Comisiones',
            'code': 'COM',
            'category_id': variable_category.id,
            'sequence': 90,
            'condition_select': 'none',
            'amount_select': 'code',
            'amount_python_compute': 'result = inputs.COM.amount if inputs.COM else 0',
            'struct_id': self.structure.id,
            'appears_on_payslip': True,
            'include_in_severance': True,  # Flag to include in severance base
        })
        
        # Create payslips with variable components for last 3 months
        today = date.today()
        for i in range(3):
            month_date = today - relativedelta(months=i)
            date_from = date(month_date.year, month_date.month, 1)
            date_to = date(month_date.year, month_date.month, calendar.monthrange(month_date.year, month_date.month)[1])
            
            # Create payslip
            payslip = self.env['hr.payslip'].create({
                'name': f'Salary Slip - {month_date.strftime("%B %Y")}',
                'employee_id': self.employee.id,
                'contract_id': self.contract.id,
                'date_from': date_from,
                'date_to': date_to,
                'struct_id': self.structure.id,
                'company_id': self.company.id,
            })
            
            # Add commission input
            commission_amount = 300000.0 + (i * 50000.0)  # Variable commission
            self.env['hr.payslip.input'].create({
                'name': 'Commission',
                'payslip_id': payslip.id,
                'input_type_id': self.env['hr.payslip.input.type'].create({
                    'name': 'Commission Input',
                    'code': 'COM',
                }).id,
                'amount': commission_amount,
            })
            
            # Compute and confirm payslip
            payslip.compute_sheet()
            payslip.action_payslip_done()
        
        # Create a severance payment calculation wizard
        wizard = self.env['hr.severance.payment.wizard'].create({
            'employee_id': self.employee.id,
            'calculation_date': today,
        })
        
        # Calculate severance
        wizard.calculate_severance()
        
        # Calculate expected amount with variable components
        # Average of last 3 months of commissions: (300000 + 350000 + 400000) / 3 = 350000
        days_worked = (today - self.contract_start).days
        expected_base = self.contract.wage + 350000.0  # Base + avg commission
        expected_amount = expected_base * days_worked / 360
        
        self.assertAlmostEqual(
            wizard.amount, 
            expected_amount, 
            delta=1.0,
            msg="Severance calculation with variable salary doesn't match expected amount"
        )
        
        # Check that variable component is reported
        self.assertAlmostEqual(
            wizard.variable_component, 
            350000.0, 
            delta=1.0,
            msg="Variable component calculation doesn't match expected amount"
        )

    def test_15_severance_with_partial_withdrawals(self):
        """Test severance calculation with previous partial withdrawals."""
        # Create a previous partial withdrawal
        withdrawal_date = date.today() - relativedelta(months=3)
        withdrawal_amount = 500000.0
        
        withdrawal = self.env['hr.severance.withdrawal'].create({
            'employee_id': self.employee.id,
            'request_date': withdrawal_date - timedelta(days=5),
            'payment_date': withdrawal_date,
            'amount': withdrawal_amount,
            'reason': 'education',
            'description': 'University tuition',
            'state': 'done',
        })
        
        # Create a severance payment calculation wizard
        wizard = self.env['hr.severance.payment.wizard'].create({
            'employee_id': self.employee.id,
            'calculation_date': date.today(),
            'include_withdrawals': True,
        })
        
        # Calculate severance
        wizard.calculate_severance()
        
        # Calculate expected amount considering withdrawal
        days_worked = (date.today() - self.contract_start).days
        expected_base_amount = self.contract.wage * days_worked / 360
        
        # Calculate interest on withdrawal amount
        days_since_withdrawal = (date.today() - withdrawal_date).days
        withdrawal_interest = withdrawal_amount * 0.12 * days_since_withdrawal / 360
        
        expected_total = expected_base_amount + withdrawal_amount + withdrawal_interest
        
        self.assertAlmostEqual(
            wizard.total_amount, 
            expected_total, 
            delta=100.0,  # Allow for calculation differences
            msg="Total severance calculation with withdrawals doesn't match expected amount"
        )
        
        # Check withdrawal reporting
        self.assertEqual(
            len(wizard.withdrawal_ids), 
            1,
            "Should have one withdrawal record"
        )
        self.assertAlmostEqual(
            wizard.withdrawal_ids[0].amount, 
            withdrawal_amount,
            places=2,
            msg="Withdrawal amount should match"
        )

    def test_16_severance_with_leave_periods(self):
        """Test severance calculation with unpaid leave periods."""
        # Create leave type
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Unpaid Leave',
            'request_unit': 'day',
            'unpaid': True,
            'exclude_public_holidays': True,
            'company_id': self.company.id,
        })
        
        # Create unpaid leave
        leave_start = date.today() - relativedelta(months=2)
        leave_end = leave_start + timedelta(days=14)  # 15-day unpaid leave
        
        leave = self.env['hr.leave'].create({
            'name': 'Unpaid Leave',
            'employee_id': self.employee.id,
            'holiday_status_id': leave_type.id,
            'date_from': datetime.combine(leave_start, time(8, 0, 0)),
            'date_to': datetime.combine(leave_end, time(17, 0, 0)),
            'number_of_days': 15,
            'state': 'validate',
        })
        
        # Create a severance payment calculation wizard
        wizard = self.env['hr.severance.payment.wizard'].create({
            'employee_id': self.employee.id,
            'calculation_date': date.today(),
        })
        
        # Calculate severance
        wizard.calculate_severance()
        
        # Calculate expected amount excluding unpaid leave
        total_days = (date.today() - self.contract_start).days
        unpaid_days = 15  # Length of unpaid leave
        working_days = total_days - unpaid_days
        
        expected_amount = self.contract.wage * working_days / 360
        
        self.assertAlmostEqual(
            wizard.amount, 
            expected_amount, 
            delta=1.0,
            msg="Severance calculation with unpaid leave doesn't match expected amount"
        )
        
        # Check that unpaid leave is reported
        self.assertEqual(
            wizard.unpaid_days, 
            unpaid_days,
            "Unpaid days should match leave duration"
        )

    def test_17_severance_with_multiple_contracts(self):
        """Test severance calculation with multiple consecutive contracts."""
        # End current contract
        first_contract_end = date.today() - relativedelta(months=6)
        self.contract.write({
            'date_end': first_contract_end,
            'state': 'close',
        })
        
        # Create second contract
        second_contract_start = first_contract_end + timedelta(days=1)
        second_contract = self.env['hr.contract'].create({
            'name': 'Second Test Contract',
            'employee_id': self.employee.id,
            'department_id': self.department.id,
            'job_id': self.job.id,
            'type_id': self.contract_type.id,
            'wage': 1800000.0,  # Higher wage
            'state': 'open',
            'date_start': second_contract_start,
            'resource_calendar_id': self.env.ref('resource.resource_calendar_std').id,
            'structure_type_id': self.structure_type.id,
            'company_id': self.company.id,
        })
        
        # Create a severance payment calculation wizard
        wizard = self.env['hr.severance.payment.wizard'].create({
            'employee_id': self.employee.id,
            'calculation_date': date.today(),
            'include_all_contracts': True,
        })
        
        # Calculate severance
        wizard.calculate_severance()
        
        # Calculate expected amount for first contract
        first_contract_days = (first_contract_end - self.contract_start).days
        first_contract_amount = self.contract.wage * first_contract_days / 360
        
        # Calculate expected amount for second contract
        second_contract_days = (date.today() - second_contract_start).days
        second_contract_amount = second_contract.wage * second_contract_days / 360
        
        # Total expected amount
        expected_amount = first_contract_amount + second_contract_amount
        
        self.assertAlmostEqual(
            wizard.amount, 
            expected_amount, 
            delta=1.0,
            msg="Severance calculation with multiple contracts doesn't match expected amount"
        )
        
        # Check contract reporting
        self.assertEqual(
            len(wizard.contract_ids), 
            2,
            "Should have two contract records"
        )

    def test_18_severance_certificate(self):
        """Test generation of severance certificate."""
        # Create a severance payment
        payment = self.env['hr.severance.payment'].create({
            'employee_id': self.employee.id,
            'calculation_date': date.today(),
            'payment_date': date.today(),
            'amount': 1500000.0,
            'state': 'done',
        })
        
        # Generate certificate
        certificate = payment.generate_certificate()
        
        # Check certificate generation
        self.assertTrue(certificate, "Certificate should be generated")
        self.assertEqual(
            certificate['res_model'], 
            'hr.severance.certificate',
            "Certificate model should be correct"
        )
        
        # Get certificate record
        cert_record = self.env['hr.severance.certificate'].browse(certificate['res_id'])
        
        # Check certificate data
        self.assertEqual(cert_record.employee_id, self.employee, "Certificate should be for correct employee")
        self.assertEqual(cert_record.year, date.today().year, "Certificate year should be current year")
        self.assertAlmostEqual(
            cert_record.amount, 
            1500000.0, 
            "Certificate amount should match payment amount",
            places=2
        )
        
        # Test certificate PDF generation
        pdf_report = self.env.ref('nomina_colombia.action_report_severance_certificate').render_qweb_pdf([cert_record.id])
        self.assertTrue(pdf_report, "PDF report should be generated")
        self.assertTrue(len(pdf_report[0]) > 0, "PDF content should not be empty")

    def test_19_severance_accounting_integration(self):
        """Test integration with accounting for severance payments."""
        # Create accounting configuration
        severance_account = self.env['account.account'].create({
            'name': 'Severance Payable',
            'code': '251010',
            'account_type': 'liability_current',
            'company_id': self.company.id,
        })
        
        expense_account = self.env['account.account'].create({
            'name': 'Severance Expense',
            'code': '510570',
            'account_type': 'expense',
            'company_id': self.company.id,
        })
        
        journal = self.env['account.journal'].create({
            'name': 'Severance Journal',
            'code': 'SEV',
            'type': 'general',
            'company_id': self.company.id,
        })
        
        # Configure payroll accounting
        self.env['res.config.settings'].create({
            'company_id': self.company.id,
            'severance_account_id': severance_account.id,
            'severance_expense_account_id': expense_account.id,
            'severance_journal_id': journal.id,
        }).execute()
        
        # Create a severance payment calculation wizard
        wizard = self.env['hr.severance.payment.wizard'].create({
            'employee_id': self.employee.id,
            'calculation_date': date.today(),
            'payment_date': date.today(),
            'journal_id': journal.id,
        })
        
        # Calculate severance
        wizard.calculate_severance()
        
        # Generate payment with accounting entries
        payment = wizard.generate_payment()
        
        # Check accounting entries
        self.assertTrue(payment.move_id, "Accounting move should be created")
        self.assertEqual(payment.move_id.journal_id, journal, "Journal should match configuration")
        self.assertEqual(payment.move_id.state, 'posted', "Move should be posted")
        
        # Check move lines
        debit_line = payment.move_id.line_ids.filtered(lambda l: l.debit > 0)
        credit_line = payment.move_id.line_ids.filtered(lambda l: l.credit > 0)
        
        self.assertEqual(debit_line.account_id, expense_account, "Debit account should be expense account")
        self.assertEqual(credit_line.account_id, severance_account, "Credit account should be severance account")
        self.assertAlmostEqual(
            debit_line.debit, 
            payment.amount, 
            "Debit amount should match payment amount",
            place=2
        )
        self.assertAlmostEqual(
            credit_line.credit, 
            payment.amount, 
            "Credit amount should match payment amount",
            places=2,
        )

    def test_20_severance_provision(self):
        """Test monthly severance provision calculation."""
        # Create provision configuration
        provision_account = self.env['account.account'].create({
            'name': 'Severance Provision',
            'code': '261005',
            'account_type': 'liability_current',
            'company_id': self.company.id,
        })
        
        expense_account = self.env['account.account'].create({
            'name': 'Severance Provision Expense',
            'code': '510570',
            'account_type': 'expense',
            'company_id': self.company.id,
        })

        # Create journal for provisions
        provision_journal = self.env['account.journal'].create({
            'name': 'Provision Journal',
            'code': 'PROV',
            'type': 'general',
            'company_id': self.company.id,
        })
        
        # Configure provision accounting
        self.env['res.config.settings'].create({
            'company_id': self.company.id,
            'severance_provision_account_id': provision_account.id,
            'severance_provision_expense_account_id': expense_account.id,
            'provision_journal_id': provision_journal.id,
        }).execute()
        
        # Create a provision calculation wizard
        today = date.today()
        month_date = date(today.year, today.month, 1)
        
        wizard = self.env['hr.provision.wizard'].create({
            'date_from': month_date,
            'date_to': date(month_date.year, month_date.month, calendar.monthrange(month_date.year, month_date.month)[1]),
            'provision_type': 'severance',
            'journal_id': provision_journal.id,
        })
        
        # Calculate provisions
        wizard.calculate_provisions()
        
        # Check employee is in provision lines
        employee_line = wizard.line_ids.filtered(lambda l: l.employee_id == self.employee)
        self.assertTrue(employee_line, "Employee should be included in provision lines")
        
        # Calculate expected provision amount (monthly portion)
        expected_monthly_provision = self.contract.wage / 12
        self.assertAlmostEqual(
            employee_line.amount, 
            expected_monthly_provision, 
            delta=1.0,
            msg="Monthly provision amount doesn't match expected amount"
        )
        
        # Process provisions
        provision = wizard.process_provisions()
        
        # Check accounting entries
        self.assertTrue(provision.move_id, "Accounting move should be created")
        self.assertEqual(provision.move_id.journal_id, provision_journal, "Journal should match configuration")
        self.assertEqual(provision.move_id.state, 'posted', "Move should be posted")
        
        # Check move lines
        debit_line = provision.move_id.line_ids.filtered(lambda l: l.debit > 0)
        credit_line = provision.move_id.line_ids.filtered(lambda l: l.credit > 0)
        
        self.assertEqual(debit_line.account_id, expense_account, "Debit account should be expense account")
        self.assertEqual(credit_line.account_id, provision_account, "Credit account should be provision account")
        self.assertAlmostEqual(
            sum(debit_line.mapped('debit')), 
            sum(wizard.line_ids.mapped('amount')), 
            "Total debit should match total provision amount",
            places=2,
        )

    def test_21_severance_interest_provision(self):
        """Test severance interest provision calculation."""
        # Create a provision calculation wizard for interest
        today = date.today()
        month_date = date(today.year, today.month, 1)
        
        wizard = self.env['hr.provision.wizard'].create({
            'date_from': month_date,
            'date_to': date(month_date.year, month_date.month, calendar.monthrange(month_date.year, month_date.month)[1]),
            'provision_type': 'severance_interest',
        })
        
        # Calculate provisions
        wizard.calculate_provisions()
        
        # Check employee is in provision lines
        employee_line = wizard.line_ids.filtered(lambda l: l.employee_id == self.employee)
        self.assertTrue(employee_line, "Employee should be included in provision lines")
        
        # Calculate expected interest provision (monthly portion of 12% annual)
        # Accumulated severance for the year so far
        days_in_year_so_far = (today - date(today.year, 1, 1)).days + 1
        severance_accumulated = self.contract.wage * days_in_year_so_far / 360
        expected_monthly_interest = severance_accumulated * 0.12 / 12
        
        self.assertAlmostEqual(
            employee_line.amount, 
            expected_monthly_interest, 
            delta=1.0,
            msg="Monthly interest provision amount doesn't match expected amount"
        )

    def test_22_severance_adjustment_for_salary_increase(self):
        """Test severance adjustment calculation for salary increases."""
        # Create initial severance calculation
        initial_date = date.today() - relativedelta(months=3)
        initial_wizard = self.env['hr.severance.payment.wizard'].create({
            'employee_id': self.employee.id,
            'calculation_date': initial_date,
        })
        initial_wizard.calculate_severance()
        initial_amount = initial_wizard.amount
        
        # Increase salary
        new_wage = self.contract.wage * 1.1  # 10% increase
        self.contract.write({
            'wage': new_wage,
            'wage_adjustment_date': date.today() - relativedelta(months=2),
        })
        
        # Create adjustment calculation wizard
        adjustment_wizard = self.env['hr.severance.adjustment.wizard'].create({
            'employee_id': self.employee.id,
            'previous_calculation_date': initial_date,
            'current_calculation_date': date.today(),
        })
        
        # Calculate adjustment
        adjustment_wizard.calculate_adjustment()
        
        # Check adjustment amount
        # Expected adjustment: difference between recalculated amount with new salary and original amount
        days_worked_initial = (initial_date - self.contract_start).days
        days_worked_current = (date.today() - self.contract_start).days
        
        # Original calculation with old salary
        original_amount = self.contract.wage * 0.9 * days_worked_current / 360  # 0.9 to reverse the 10% increase
        
        # New calculation with new salary
        new_amount = new_wage * days_worked_current / 360
        
        # Expected adjustment is the difference
        expected_adjustment = new_amount - original_amount
        
        self.assertAlmostEqual(
            adjustment_wizard.adjustment_amount, 
            expected_adjustment, 
            delta=100.0,  # Allow for calculation differences
            msg="Adjustment amount doesn't match expected amount"
        )
        
        # Process adjustment
        adjustment = adjustment_wizard.process_adjustment()
        
        # Check adjustment record
        self.assertTrue(adjustment, "Adjustment record should be created")
        self.assertEqual(adjustment.employee_id, self.employee, "Adjustment should be for correct employee")
        self.assertEqual(adjustment.adjustment_type, 'salary_increase', "Adjustment type should be salary increase")

    def test_23_severance_fund_report(self):
        """Test severance fund report generation."""
        # Create several employees with the same fund
        employees = [self.employee]
        for i in range(3):
            emp = self.env['hr.employee'].create({
                'name': f'Fund Report Employee {i+1}',
                'identification_id': f'8765432{i}',
                'gender': 'male' if i % 2 == 0 else 'female',
                'country_id': self.env.ref('base.co').id,
                'department_id': self.department.id,
                'company_id': self.company.id,
                'severance_fund_id': self.severance_fund.id,
            })
            employees.append(emp)
            
            # Create contract
            self.env['hr.contract'].create({
                'name': f'Fund Report Contract {i+1}',
                'employee_id': emp.id,
                'department_id': self.department.id,
                'job_id': self.job.id,
                'type_id': self.contract_type.id,
                'wage': 1000000.0 + (i * 200000.0),
                'state': 'open',
                'date_start': date.today() - relativedelta(months=i+3),
                'resource_calendar_id': self.env.ref('resource.resource_calendar_std').id,
                'structure_type_id': self.structure_type.id,
                'company_id': self.company.id,
            })
        
        # Create fund report wizard
        wizard = self.env['hr.severance.fund.report.wizard'].create({
            'fund_id': self.severance_fund.id,
            'date': date.today(),
            'report_type': 'detailed',
        })
        
        # Generate report
        report = wizard.generate_report()
        
        # Check report data
        self.assertTrue(report, "Report should be generated")
        self.assertEqual(report['type'], 'ir.actions.report', "Should return a report action")
        
        # Get report model
        report_model = self.env['hr.severance.fund.report'].search([
            ('fund_id', '=', self.severance_fund.id),
            ('date', '=', date.today())
        ], limit=1)
        
        self.assertTrue(report_model, "Report record should be created")
        self.assertEqual(len(report_model.line_ids), len(employees), "Report should include all employees")
        self.assertTrue(report_model.total_amount > 0, "Total amount should be greater than zero")

    def test_24_severance_history_tracking(self):
        """Test severance payment history tracking."""
        # Create several severance payments over time
        payments = []
        for i in range(3):
            payment_date = date.today() - relativedelta(years=i)
            payment = self.env['hr.severance.payment'].create({
                'employee_id': self.employee.id,
                'calculation_date': payment_date,
                'payment_date': payment_date,
                'amount': 1000000.0 + (i * 200000.0),
                'state': 'done',
            })
            payments.append(payment)
        
        # Create history report wizard
        wizard = self.env['hr.severance.history.wizard'].create({
            'employee_id': self.employee.id,
            'date_from': date.today() - relativedelta(years=3),
            'date_to': date.today(),
        })
        
        # Generate history report
        report = wizard.generate_report()
        
        # Check report data
        self.assertTrue(report, "Report should be generated")
        
        # Get report model
        report_model = self.env['hr.severance.history'].search([
            ('employee_id', '=', self.employee.id),
            ('date_from', '=', wizard.date_from),
            ('date_to', '=', wizard.date_to)
        ], limit=1)
        
        self.assertTrue(report_model, "History record should be created")
        self.assertEqual(len(report_model.line_ids), len(payments), "History should include all payments")
        
        # Check total amount
        expected_total = sum(p.amount for p in payments)
        self.assertAlmostEqual(
            report_model.total_amount, 
            expected_total, 
            places=2,
            msg="Total amount should match sum of payments"
        )

    def test_25_severance_with_work_schedule_changes(self):
        """Test severance calculation with work schedule changes."""
        # Create part-time schedule
        part_time = self.env['resource.calendar'].create({
            'name': 'Part Time 20h',
            'company_id': self.company.id,
            'hours_per_day': 4,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12}),
            ],
        })
        
        # Change contract to part-time halfway through
        schedule_change_date = date.today() - relativedelta(months=3)
        
        # Create contract history
        self.env['hr.contract.schedule.history'].create({
            'contract_id': self.contract.id,
            'resource_calendar_id': self.env.ref('resource.resource_calendar_std').id,
            'date_start': self.contract_start,
            'date_end': schedule_change_date - timedelta(days=1),
        })
        
        self.env['hr.contract.schedule.history'].create({
            'contract_id': self.contract.id,
            'resource_calendar_id': part_time.id,
            'date_start': schedule_change_date,
            'date_end': False,
        })
        
        # Update contract with current schedule
        self.contract.write({
            'resource_calendar_id': part_time.id,
            'schedule_change_date': schedule_change_date,
        })
        
        # Create a severance payment calculation wizard
        wizard = self.env['hr.severance.payment.wizard'].create({
            'employee_id': self.employee.id,
            'calculation_date': date.today(),
            'consider_schedule_changes': True,
        })
        
        # Calculate severance
        wizard.calculate_severance()
        
        # Calculate expected amount with schedule changes
        # Full-time period
        full_time_days = (schedule_change_date - self.contract_start).days
        full_time_amount = self.contract.wage * full_time_days / 360
        
        # Part-time period (50% of full-time)
        part_time_days = (date.today() - schedule_change_date).days
        part_time_amount = (self.contract.wage * 0.5) * part_time_days / 360
        
        expected_amount = full_time_amount + part_time_amount
        
        self.assertAlmostEqual(
            wizard.amount, 
            expected_amount, 
            delta=100.0,  # Allow for calculation differences
            msg="Severance calculation with schedule changes doesn't match expected amount"
        )