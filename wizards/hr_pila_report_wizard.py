from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import base64
import calendar
import logging
import xlsxwriter
from io import BytesIO

_logger = logging.getLogger(__name__)

class HrPilaReportWizard(models.TransientModel):
    _name = 'hr.pila.report.wizard'
    _description = 'Asistente de Reportes PILA'

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

    report_type = fields.Selection([
        ('summary', 'Resumen PILA'),
        ('detailed', 'Detalle por Empleado'),
        ('comparative', 'Comparativo Mensual'),
        ('funds', 'Resumen por Fondos'),
        ('errors', 'Reporte de Errores')
    ], string='Tipo de Reporte', required=True, default='summary')

    # Filtros
    department_ids = fields.Many2many(
        'hr.department',
        string='Departamentos'
    )

    employee_ids = fields.Many2many(
        'hr.employee',
        string='Empleados'
    )

    fund_types = fields.Selection([
        ('all', 'Todos los Fondos'),
        ('pension', 'Fondos de Pensión'),
        ('health', 'EPS'),
        ('arl', 'ARL'),
        ('ccf', 'Cajas de Compensación')
    ], string='Tipo de Fondo', default='all')

    # Opciones de Formato
    format_type = fields.Selection([
        ('pdf', 'PDF'),
        ('xlsx', 'Excel'),
        ('csv', 'CSV')
    ], string='Formato de Salida', required=True, default='xlsx')

    include_subtotals = fields.Boolean(
        string='Incluir Subtotales',
        default=True
    )

    show_inactive = fields.Boolean(
        string='Mostrar Inactivos',
        help='Incluir empleados inactivos en el período'
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

    def action_generate_report(self):
        """Genera el reporte según la configuración seleccionada"""
        self.ensure_one()

        try:
            # Obtener datos según tipo de reporte
            data = self._get_report_data()

            # Generar reporte en el formato seleccionado
            if self.format_type == 'pdf':
                return self._generate_pdf_report(data)
            elif self.format_type == 'xlsx':
                return self._generate_excel_report(data)
            else:
                return self._generate_csv_report(data)

        except Exception as e:
            _logger.error("Error generando reporte PILA: %s", str(e))
            raise ValidationError(_('Error generando reporte: %s') % str(e))

    def _get_report_data(self):
        """Obtiene los datos según el tipo de reporte"""
        method_name = f'_get_{self.report_type}_data'
        if not hasattr(self, method_name):
            raise ValidationError(_('Tipo de reporte no implementado'))
        return getattr(self, method_name)()

    def _get_summary_data(self):
        """Obtiene datos para el reporte resumen"""
        # Obtener registros PILA del período
        domain = [
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('state', 'in', ['validated', 'sent', 'done'])
        ]

        pila_records = self.env['hr.pila'].search(domain)

        if not pila_records:
            raise ValidationError(_('No se encontraron registros PILA para el período seleccionado'))

        # Preparar datos
        summary_data = {
            'total_employees': 0,
            'total_health': 0,
            'total_pension': 0,
            'total_arl': 0,
            'total_ccf': 0,
            'total_amount': 0,
            'by_department': {},
            'by_fund': {
                'pension': {},
                'health': {},
                'arl': {},
                'ccf': {}
            }
        }

        # Procesar registros
        for pila in pila_records:
            summary_data['total_employees'] += pila.total_employees
            summary_data['total_health'] += pila.total_health
            summary_data['total_pension'] += pila.total_pension
            summary_data['total_arl'] += pila.total_arl
            summary_data['total_ccf'] += pila.total_ccf
            summary_data['total_amount'] += pila.total_amount

            # Agrupar por departamento
            for line in pila.pila_line_ids:
                dept_id = line.employee_id.department_id.id
                if dept_id not in summary_data['by_department']:
                    summary_data['by_department'][dept_id] = {
                        'name': line.employee_id.department_id.name,
                        'employees': 0,
                        'total': 0
                    }
                summary_data['by_department'][dept_id]['employees'] += 1
                summary_data['by_department'][dept_id]['total'] += line.total_amount

                # Agrupar por fondo
                self._update_fund_totals(summary_data['by_fund'], line)

        return summary_data

    def _get_detailed_data(self):
        """Obtiene datos detallados por empleado"""
        domain = [
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('state', 'in', ['validated', 'sent', 'done'])
        ]

        if self.department_ids:
            domain.append(('employee_id.department_id', 'in', self.department_ids.ids))
        if self.employee_ids:
            domain.append(('employee_id', 'in', self.employee_ids.ids))

        pila_lines = self.env['hr.pila.line'].search(domain)

        if not pila_lines:
            raise ValidationError(_('No se encontraron registros para el período seleccionado'))

        detailed_data = []
        for line in pila_lines:
            detailed_data.append({
                'employee': line.employee_id.name,
                'identification': line.employee_id.identification_id,
                'department': line.employee_id.department_id.name,
                'pension_fund': line.pension_fund_id.name,
                'health_fund': line.health_fund_id.name,
                'arl': line.arl_id.name,
                'ccf': line.ccf_id.name,
                'wage': line.wage,
                'health_base': line.health_base,
                'pension_base': line.pension_base,
                'arl_base': line.arl_base,
                'health_amount': line.health_amount,
                'pension_amount': line.pension_amount,
                'arl_amount': line.arl_amount,
                'ccf_amount': line.ccf_amount,
                'total_amount': line.total_amount
            })

        return detailed_data

    def _get_comparative_data(self):
        """Obtiene datos para reporte comparativo mensual"""
        # Calcular rango de meses
        months = []
        current_date = self.date_from
        while current_date <= self.date_to:
            months.append(current_date)
            # Avanzar al siguiente mes
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)

        comparative_data = {
            'months': months,
            'totals': {},
            'by_department': {},
            'by_fund': {}
        }

        for month in months:
            last_day = calendar.monthrange(month.year, month.month)[1]
            month_end = month.replace(day=last_day)

            # Obtener registros del mes
            pila_records = self.env['hr.pila'].search([
                ('date_from', '>=', month),
                ('date_to', '<=', month_end),
                ('state', 'in', ['validated', 'sent', 'done'])
            ])

            month_key = month.strftime('%Y-%m')
            comparative_data['totals'][month_key] = {
                'employees': 0,
                'health': 0,
                'pension': 0,
                'arl': 0,
                'ccf': 0,
                'total': 0
            }

            for pila in pila_records:
                comparative_data['totals'][month_key]['employees'] += pila.total_employees
                comparative_data['totals'][month_key]['health'] += pila.total_health
                comparative_data['totals'][month_key]['pension'] += pila.total_pension
                comparative_data['totals'][month_key]['arl'] += pila.total_arl
                comparative_data['totals'][month_key]['ccf'] += pila.total_ccf
                comparative_data['totals'][month_key]['total'] += pila.total_amount

        return comparative_data

    def _get_funds_data(self):
        """Obtiene datos para reporte de fondos"""
        domain = [
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('state', 'in', ['validated', 'sent', 'done'])
        ]

        pila_lines = self.env['hr.pila.line'].search(domain)

        funds_data = {
            'pension': {},
            'health': {},
            'arl': {},
            'ccf': {}
        }

        for line in pila_lines:
            # Fondos de pensión
            if line.pension_fund_id:
                fund_id = line.pension_fund_id.id
                if fund_id not in funds_data['pension']:
                    funds_data['pension'][fund_id] = {
                        'name': line.pension_fund_id.name,
                        'employees': 0,
                        'base': 0,
                        'amount': 0
                    }
                funds_data['pension'][fund_id]['employees'] += 1
                funds_data['pension'][fund_id]['base'] += line.pension_base
                funds_data['pension'][fund_id]['amount'] += line.pension_amount

            # EPS
            if line.health_fund_id:
                fund_id = line.health_fund_id.id
                if fund_id not in funds_data['health']:
                    funds_data['health'][fund_id] = {
                        'name': line.health_fund_id.name,
                        'employees': 0,
                        'base': 0,
                        'amount': 0
                    }
                funds_data['health'][fund_id]['employees'] += 1
                funds_data['health'][fund_id]['base'] += line.health_base
                funds_data['health'][fund_id]['amount'] += line.health_amount

            # Procesar otros fondos...

        return funds_data

    def _generate_excel_report(self, data):
        """Genera reporte en formato Excel"""
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)

        # Formatos
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'fg_color': '#D3D3D3',
            'border': 1
        })

        number_format = workbook.add_format({
            'num_format': '#,##0.00',
            'border': 1
        })

        # Generar hojas según tipo de reporte
        method_name = f'_generate_excel_{self.report_type}'
        if hasattr(self, method_name):
            getattr(self, method_name)(workbook, data, header_format, number_format)

        workbook.close()
        content = output.getvalue()

        # Crear adjunto
        attachment = self.env['ir.attachment'].create({
            'name': f'PILA_{self.report_type}_{self.date_from.strftime("%Y%m")}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(content),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def _update_fund_totals(self, fund_data, line):
        """Actualiza totales por fondo"""
        # Pensión
        if line.pension_fund_id:
            fund_id = line.pension_fund_id.id
            if fund_id not in fund_data['pension']:
                fund_data['pension'][fund_id] = {
                    'name': line.pension_fund_id.name,
                    'amount': 0
                }
            fund_data['pension'][fund_id]['amount'] += line.pension_amount

        # Salud
        if line.health_fund_id:
            fund_id = line.health_fund_id.id
            if fund_id not in fund_data['health']:
                fund_data['health'][fund_id] = {
                    'name': line.health_fund_id.name,
                    'amount': 0
                }
            fund_data['health'][fund_id]['amount'] += line.health_amount

        # ARL
        if line.arl_id:
            fund_id = line.arl_id.id
            if fund_id not in fund_data['arl']:
                fund_data['arl'][fund_id] = {
                    'name': line.arl_id.name,
                    'amount': 0
                }
            fund_data['arl'][fund_id]['amount'] += line.arl_amount

        # CCF
        if line.ccf_id:
            fund_id = line.ccf_id.id
            if fund_id not in fund_data['ccf']:
                fund_data['ccf'][fund_id] = {
                    'name': line.ccf_id.name,
                    'amount': 0
                }
            fund_data['ccf'][fund_id]['amount'] += line.ccf_amount