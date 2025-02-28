from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import calendar
import logging

_logger = logging.getLogger(__name__)

class HrPayrollProvisionWizard(models.TransientModel):
    _name = 'hr.payroll.provision.wizard'
    _description = 'Asistente de Cálculo de Provisiones'

    # Campos Básicos
    date_from = fields.Date(
        string='Fecha Inicial',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1)
    )

    date_to = fields.Date(
        string='Fecha Final',
        required=True,
        default=lambda self: fields.Date.today().replace(
            day=calendar.monthrange(
                fields.Date.today().year,
                fields.Date.today().month
            )[1]
        )
    )

    # Tipos de Provisiones
    provision_types = fields.Selection([
        ('all', 'Todas las Provisiones'),
        ('prima', 'Prima de Servicios'),
        ('cesantias', 'Cesantías'),
        ('intereses', 'Intereses de Cesantías'),
        ('vacaciones', 'Vacaciones')
    ], string='Tipo de Provisión', required=True, default='all')

    # Filtros
    department_ids = fields.Many2many(
        'hr.department',
        string='Departamentos',
        help='Dejar vacío para todos los departamentos'
    )

    employee_ids = fields.Many2many(
        'hr.employee',
        string='Empleados',
        help='Dejar vacío para todos los empleados'
    )

    # Opciones de Contabilización
    generate_journal_entries = fields.Boolean(
        string='Generar Asientos Contables',
        default=True
    )

    journal_id = fields.Many2one(
        'account.journal',
        string='Diario Contable',
        domain=[('type', '=', 'general')]
    )

    move_date = fields.Date(
        string='Fecha Contable',
        default=fields.Date.today
    )

    # Opciones Adicionales
    recalculate = fields.Boolean(
        string='Recalcular Existentes',
        help='Recalcular provisiones ya existentes en el período'
    )

    detailed_report = fields.Boolean(
        string='Reporte Detallado',
        default=True,
        help='Incluir detalles en el reporte de provisiones'
    )

    @api.onchange('date_from')
    def _onchange_date_from(self):
        if self.date_from:
            # Establecer último día del mes para fecha final
            last_day = calendar.monthrange(
                self.date_from.year,
                self.date_from.month
            )[1]
            self.date_to = self.date_from.replace(day=last_day)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_to < record.date_from:
                raise ValidationError(_('La fecha final debe ser mayor a la fecha inicial'))

    def action_calculate_provisions(self):
        """Calcula las provisiones según la configuración"""
        self.ensure_one()

        try:
            # Validar configuración
            self._validate_configuration()

            # Obtener empleados
            employees = self._get_employees()

            if not employees:
                raise ValidationError(_('No se encontraron empleados para calcular provisiones'))

            # Calcular provisiones
            provisions = self._calculate_provisions(employees)

            # Generar asientos contables si es necesario
            if self.generate_journal_entries:
                move = self._create_journal_entries(provisions)

            # Crear registro de provisiones
            provision_record = self._create_provision_record(provisions)

            # Generar reporte
            return self._generate_provision_report(provision_record)

        except Exception as e:
            _logger.error("Error calculando provisiones: %s", str(e))
            raise ValidationError(_('Error en cálculo de provisiones: %s') % str(e))

    def _validate_configuration(self):
        """Valida la configuración necesaria"""
        if self.generate_journal_entries:
            if not self.journal_id:
                raise ValidationError(_('Debe seleccionar un diario contable'))

            # Validar cuentas contables
            company = self.env.company
            if not company.provision_prima_account_id or \
               not company.provision_cesantias_account_id or \
               not company.provision_intereses_account_id or \
               not company.provision_vacaciones_account_id:
                raise ValidationError(_('Faltan configurar cuentas contables para provisiones'))

    def _get_employees(self):
        """Obtiene los empleados según filtros"""
        domain = [('contract_id.state', '=', 'open')]

        if self.department_ids:
            domain.append(('department_id', 'in', self.department_ids.ids))

        if self.employee_ids:
            domain.append(('id', 'in', self.employee_ids.ids))

        return self.env['hr.employee'].search(domain)

    def _calculate_provisions(self, employees):
        """Calcula provisiones para los empleados"""
        provisions = []
        
        for employee in employees:
            contract = employee.contract_id
            if not contract:
                continue

            # Calcular base para provisiones
            base = self._calculate_provision_base(contract)

            # Calcular provisiones según tipo seleccionado
            if self.provision_types in ['all', 'prima']:
                prima = self._calculate_prima(contract, base)
                provisions.append({
                    'employee_id': employee.id,
                    'type': 'prima',
                    'base_amount': base,
                    'amount': prima,
                    'date': self.date_to
                })

            if self.provision_types in ['all', 'cesantias']:
                cesantias = self._calculate_cesantias(contract, base)
                provisions.append({
                    'employee_id': employee.id,
                    'type': 'cesantias',
                    'base_amount': base,
                    'amount': cesantias,
                    'date': self.date_to
                })

            if self.provision_types in ['all', 'intereses']:
                intereses = self._calculate_intereses(contract, base)
                provisions.append({
                    'employee_id': employee.id,
                    'type': 'intereses',
                    'base_amount': base,
                    'amount': intereses,
                    'date': self.date_to
                })

            if self.provision_types in ['all', 'vacaciones']:
                vacaciones = self._calculate_vacaciones(contract, base)
                provisions.append({
                    'employee_id': employee.id,
                    'type': 'vacaciones',
                    'base_amount': base,
                    'amount': vacaciones,
                    'date': self.date_to
                })

        return provisions

    def _calculate_provision_base(self, contract):
        """Calcula la base para provisiones"""
        # Obtener nóminas del período
        payslips = self.env['hr.payslip'].search([
            ('employee_id', '=', contract.employee_id.id),
            ('state', 'in', ['done', 'paid']),
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to)
        ])

        base_amount = 0
        for payslip in payslips:
            # Sumar conceptos base para provisiones
            for line in payslip.line_ids:
                if line.salary_rule_id.include_in_provisions:
                    base_amount += line.total

        return base_amount

    def _calculate_prima(self, contract, base_amount):
        """Calcula provisión de prima"""
        # Prima = (Salario + Auxilio de Transporte) / 12
        transport = contract.transport_allowance or 0
        return (base_amount + transport) * 0.0833  # (1/12)

    def _calculate_cesantias(self, contract, base_amount):
        """Calcula provisión de cesantías"""
        # Cesantías = (Salario + Auxilio de Transporte) / 12
        transport = contract.transport_allowance or 0
        return (base_amount + transport) * 0.0833  # (1/12)

    def _calculate_intereses(self, contract, base_amount):
        """Calcula provisión de intereses de cesantías"""
        # Intereses = Cesantías * 12%
        cesantias = self._calculate_cesantias(contract, base_amount)
        return cesantias * 0.12

    def _calculate_vacaciones(self, contract, base_amount):
        """Calcula provisión de vacaciones"""
        # Vacaciones = Salario / 24 (15 días por año)
        return base_amount * 0.0417  # (1/24)

    def _create_journal_entries(self, provisions):
        """Crea asientos contables para las provisiones"""
        MoveLine = self.env['account.move.line']
        company = self.env.company

        # Agrupar provisiones por tipo
        provisions_by_type = {}
        for provision in provisions:
            ptype = provision['type']
            if ptype not in provisions_by_type:
                provisions_by_type[ptype] = 0
            provisions_by_type[ptype] += provision['amount']

        # Crear asiento contable
        move_vals = {
            'journal_id': self.journal_id.id,
            'date': self.move_date,
            'ref': f'Provisiones {self.date_from.strftime("%m/%Y")}',
            'line_ids': []
        }

        # Crear líneas de asiento
        for ptype, amount in provisions_by_type.items():
            # Cuenta de gasto
            expense_account = getattr(company, f'provision_{ptype}_expense_account_id')
            move_vals['line_ids'].append((0, 0, {
                'name': f'Provisión {ptype.title()}',
                'account_id': expense_account.id,
                'debit': amount,
                'credit': 0,
            }))

            # Cuenta de provisión
            provision_account = getattr(company, f'provision_{ptype}_account_id')
            move_vals['line_ids'].append((0, 0, {
                'name': f'Provisión {ptype.title()}',
                'account_id': provision_account.id,
                'debit': 0,
                'credit': amount,
            }))

        # Crear asiento
        move = self.env['account.move'].create(move_vals)
        move.action_post()

        return move

    def _create_provision_record(self, provisions):
        """Crea registro de provisiones"""
        return self.env['hr.provision'].create({
            'name': f'PROV/{self.date_from.strftime("%m/%Y")}',
            'date_from': self.date_from,
            'date_to': self.date_to,
            'provision_type': self.provision_types,
            'state': 'done',
            'provision_line_ids': [(0, 0, provision) for provision in provisions]
        })

    def _generate_provision_report(self, provision_record):
        """Genera reporte de provisiones"""
        if self.detailed_report:
            return self.env.ref('nomina_colombia.action_report_provision_detailed').report_action(provision_record)
        return self.env.ref('nomina_colombia.action_report_provision_summary').report_action(provision_record)