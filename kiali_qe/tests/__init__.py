import random
import re

from kiali_qe.components import (
    BreadCrumb,
    wait_to_spinner_disappear,
    wait_displayed,
    ListViewAbstract
)
from kiali_qe.components.enums import (
    ServicesPageFilter,
    IstioConfigPageFilter,
    WorkloadsPageFilter,
    ApplicationsPageFilter,
    OverviewPageFilter,
    IstioConfigObjectType as OBJECT_TYPE,
    IstioConfigValidation,
    MetricsSource,
    MetricsHistograms,
    InboundMetricsFilter,
    OutboundMetricsFilter,
    TimeIntervalUIText,
    GraphRefreshInterval,
    OverviewPageType,
    RoutingWizardType,
    ApplicationsPageSort,
    OverviewPageSort,
    WorkloadsPageSort,
    ServicesPageSort,
    IstioConfigPageSort,
    RoutingWizardTLS,
    RoutingWizardLoadBalancer,
    TrafficType
)
from kiali_qe.utils import is_equal, is_sublist, word_in_text
from kiali_qe.utils.log import logger

from kiali_qe.pages import (
    ServicesPage,
    IstioConfigPage,
    WorkloadsPage,
    ApplicationsPage,
    OverviewPage,
    DistributedTracingPage
)


class AbstractListPageTest(object):
    FILTER_ENUM = None
    SORT_ENUM = None
    SELECT_ITEM = ListViewAbstract.ITEMS + '//a[text()="{}"]'
    SELECT_ITEM_WITH_NAMESPACE = SELECT_ITEM + '/../../td[contains(text(), "{}")]/..//a'

    def __init__(self, kiali_client, openshift_client, page):
        self.kiali_client = kiali_client
        self.openshift_client = openshift_client
        self.page = page

    def _namespaces_ui(self):
        return self.page.namespace.items

    def get_mesh_wide_tls(self):
        return self.page.content.get_mesh_wide_tls()

    def assert_all_items(self, namespaces=[], filters=[], force_clear_all=True):
        """
        Apply supplied filter in to UI, REST, OC and assert content

        Parameters
        ----------
        namespaces: list of namespace names
        filters : list
            A list for filter. filter should be a dict.
            filter = {'name': 'Namespace', 'value': 'bookinfo'}
            Take filter name from pre defined enum
        force_clear_all : boolean
            Default True.
            If this value is True, all existing applied filters will be removed.
            otherwise, will be adjusted with pre filter.
            on both case final outcome will be same.
        """
        raise NotImplementedError('This method should be implemented on sub class')

    def get_additional_filters(self, namespaces, current_filters):
        raise NotImplementedError('This method should be implemented on sub class')

    def open(self, name, namespace=None, force_refresh=False):
        # TODO added wait for unstable performance
        wait_to_spinner_disappear(self.browser)
        if namespace is not None:
            self.browser.click(self.browser.element(
                self.SELECT_ITEM_WITH_NAMESPACE.format(name, namespace), parent=self))
        else:
            self.browser.click(self.browser.element(self.SELECT_ITEM.format(name), parent=self))

        if force_refresh:
            self.page.page_refresh()
        wait_to_spinner_disappear(self.browser)
        wait_displayed(self.page.content)

    def is_in_details_page(self, name, namespace):
        breadcrumb = BreadCrumb(self.page)
        if len(breadcrumb.locations) < 3:
            return False
        menu_location = breadcrumb.locations[0]
        if menu_location != self.page.PAGE_MENU:
            return False
        namespace_location = breadcrumb.locations[1]
        if namespace_location != "Namespace: " + namespace:
            return False
        object_location = breadcrumb.active_location
        if object_location != "{}".format(name):
            return False
        return True

    def apply_namespaces(self, namespaces, force_clear_all=False):
        """
        Apply supplied namespaces in to UI and assert with supplied and applied namespaces

        Parameters
        ----------
        namespaces : list
            A list for namespace names      .
        force_clear_all : boolean
            Default False.
            If this value is True, all existing applied namespaces will be removed.
        """
        _pre_filters = []
        # clear all filters
        if force_clear_all:
            self.page.namespace.clear_all()
            assert len(self.page.namespace.checked_items) == 0
        else:
            _pre_filters.extend(self.page.namespace.checked_items)

        # apply namespaces
        for _filter in namespaces:
            if _filter not in _pre_filters:
                self.page.namespace.check(_filter)
            if _filter in _pre_filters:
                _pre_filters.remove(_filter)
        # remove filters not in list
        for _filter in _pre_filters:
            self.page.namespace.uncheck(_filter)

        self.assert_applied_namespaces(namespaces)

    def apply_filters(self, filters, force_clear_all=False):
        """
        Apply supplied filter in to UI and assert with supplied and applied filters

        Parameters
        ----------
        filters : list
            A list for filter. filter should be a dict.
            filter = {'name': 'Health', 'value': 'Healthy'}
            Take filter name from pre defined enum
        force_clear_all : boolean
            Default False.
            If this value is True, all existing applied filters will be removed.
            otherwise, will be adjusted with pre filter.
            on both case final outcome will be same.
        """
        _pre_filters = []
        # clear all filters
        if force_clear_all:
            self.page.filter.clear_all()
            assert len(self.page.filter.active_filters) == 0
        else:
            _pre_filters.extend(self.page.filter.active_filters)

        # apply filter
        for _filter in filters:
            if _filter not in _pre_filters:
                self.page.filter.apply(filter_name=_filter['name'], value=_filter['value'])
            if _filter in _pre_filters:
                _pre_filters.remove(_filter)
        # remove filters not in list
        for _filter in _pre_filters:
            self.page.filter.remove(filter_name=_filter['name'], value=_filter['value'])

        self.assert_applied_filters(filters)

    def assert_filter_options(self):
        # test available options
        options_defined = [item.text for item in self.FILTER_ENUM]
        options_listed = self.page.filter.filters
        logger.debug('Options[defined:{}, defined:{}]'.format(options_defined, options_listed))
        assert is_equal(options_defined, options_listed), \
            'Defined: {}  Listed: {}'.format(options_defined, options_listed)

    def assert_applied_filters(self, filters):
        # validate applied filters
        _active_filters = self.page.filter.active_filters
        logger.debug('Filters[applied:{}, active:{}]'.format(filters, _active_filters))
        assert is_equal(filters, _active_filters), \
            'Defined: {}  Listed: {}'.format(filters, _active_filters)

    def assert_applied_namespaces(self, filters):
        # validate applied namespaces
        _active_filters = self.page.namespace.checked_items
        logger.debug('Filters[applied:{}, active:{}]'.format(filters, _active_filters))
        assert is_equal(filters, _active_filters), \
            'Defined: {}  Listed: {}'.format(filters, _active_filters)

    def assert_namespaces(self):
        namespaces_ui = self._namespaces_ui()
        namespaces_rest = self.kiali_client.namespace_list()
        namespaces_oc = self.openshift_client.namespace_list()
        logger.debug('Namespaces UI:{}'.format(namespaces_ui))
        logger.debug('Namespaces REST:{}'.format(namespaces_rest))
        logger.debug('Namespaces OC:{}'.format(namespaces_oc))
        assert is_equal(namespaces_ui, namespaces_rest)
        assert is_sublist(namespaces_rest, namespaces_oc)

    def assert_filter_feature_random(self):
        # clear filters if any
        # TODO: do we need to fail the test if we have filter defined before test?
        logger.debug('Filters before test:{}'.format(self.page.filter.active_filters))
        self.page.filter.clear_all()

        # get namespaces
        namespaces_ui = self._namespaces_ui()
        # apply a namespace filter
        # generate random filters list
        _defined_filters = []
        # random namespace filters
        assert len(namespaces_ui) > 0
        if len(namespaces_ui) > 3:
            _random_namespaces = random.sample(namespaces_ui, 3)
        else:
            _random_namespaces = namespaces_ui
        # add additional filters
        logger.debug('Adding additional filters')
        _defined_filters.extend(self.get_additional_filters(_random_namespaces, _defined_filters))
        logger.debug('Defined filters with additional filters:{}'.format(_defined_filters))

        # apply filters test
        _applied_filters = []
        for _defined_filter in _defined_filters:
            # add it in to applied list
            _applied_filters.append(_defined_filter)
            # apply filter and check the contents
            self.assert_all_items(namespaces=_random_namespaces,
                                  filters=_applied_filters,
                                  force_clear_all=False)

        # remove filters test
        for _defined_filter in _defined_filters:
            # remove it from our list
            _applied_filters.remove(_defined_filter)
            # apply filter and check the contents
            self.assert_all_items(namespaces=_random_namespaces,
                                  filters=_applied_filters,
                                  force_clear_all=False)
            # test remove all
            if len(_applied_filters) == 2:
                self.assert_all_items(namespaces=[], filters=[], force_clear_all=True)
                break

    def sort(self, sort_options=[]):
        """
        Sorts the listed items.

        Parameters
        ----------
        sort_options : array of 2 values
            option: SortEnum item, the sorting option to select
            is_ascending: boolean, sort ascending or descending
        """
        if len(sort_options) == 2:
            self.page.sort.select(sort_options[0], sort_options[1])

    def assert_sort_options(self):
        # test available options
        options_defined = [item.text for item in self.SORT_ENUM]
        options_listed = self.page.sort.options
        logger.debug('Options[defined:{}, defined:{}]'.format(options_defined, options_listed))
        assert is_equal(options_defined, options_listed), \
            'Defined: {}  Listed: {}'.format(options_defined, options_listed)

    def assert_metrics_options(self, metrics_page):
        metrics_page.open()
        self._assert_metrics_settings(metrics_page)
        self._assert_metrics_destination(metrics_page)
        self._assert_metrics_duration(metrics_page)
        self._assert_metrics_interval(metrics_page)

    def _assert_metrics_settings(self, metrics_page):
        # test available filters
        options_defined = [item.text for item in (
            InboundMetricsFilter if "Inbound" in metrics_page.tab_name
            else OutboundMetricsFilter)]
        for item in MetricsHistograms:
            options_defined.append(item.text)
        options_listed = metrics_page.filter.items
        logger.debug('Filter options[defined:{}, listed:{}]'
                     .format(options_defined, options_listed))
        assert is_equal(options_defined, options_listed), \
            ('Filter Options mismatch: defined:{}, listed:{}'
             .format(options_defined, options_listed))
        # enable disable each filter
        for filter_name in options_listed:
            self._filter_test(metrics_page, filter_name)

    def _filter_test(self, page, filter_name, uncheck=True):
        # TODO 'Quantile 0.nnn' item's text is 2 lines
        if "Quantile" in str(filter_name):
            return
        # test filter checked
        page.filter.check(filter_name)
        assert page.filter.is_checked(filter_name) is True
        if uncheck:
            # test filter unchecked
            page.filter.uncheck(filter_name)
            assert page.filter.is_checked(filter_name) is False

    def _assert_metrics_destination(self, metrics_page):
        self._assert_metrics_options(metrics_page, MetricsSource, 'destination')

    def _assert_metrics_duration(self, metrics_page):
        self._assert_metrics_options(metrics_page, TimeIntervalUIText, 'duration')

    def _assert_metrics_interval(self, metrics_page):
        self._assert_metrics_options(metrics_page, GraphRefreshInterval, 'interval')

    def _assert_metrics_options(self, metrics_page, enum, attr_name):
        options_defined = [item.text for item in enum]
        attr = getattr(metrics_page, attr_name)
        options_listed = attr.options
        logger.debug('Options[defined:{}, listed:{}]'.format(options_defined, options_listed))
        assert is_equal(options_defined, options_listed), \
            ('Options mismatch: defined:{}, listed:{}'.format(options_defined, options_listed))

    def assert_breadcrumb_menu(self, name, namespace):
        breadcrumb = self.load_details_page(name, namespace, force_refresh=False, load_only=True)
        menu_location = breadcrumb.locations[0]
        assert menu_location == self.page.PAGE_MENU
        breadcrumb.click_location(menu_location)
        self.assert_applied_namespaces(filters=[namespace])

    def assert_breadcrumb_namespace(self, name, namespace):
        breadcrumb = self.load_details_page(name, namespace, force_refresh=False, load_only=True)
        namespace_location = breadcrumb.locations[1]
        assert namespace_location == "Namespace: " + namespace
        breadcrumb.click_location(namespace_location)
        self.assert_applied_namespaces(filters=[namespace])

    def assert_breadcrumb_object(self, name, namespace):
        breadcrumb = self.load_details_page(name, namespace, force_refresh=False, load_only=True)
        object_location = breadcrumb.active_location
        assert object_location == "{}".format(name)

    def assert_traces_tab(self, traces_tab):
        traces_tab.open()
        assert not traces_tab.traces.is_oc_login_displayed, "OC Login should not be displayed"
        if not traces_tab.traces.has_no_results:
            assert traces_tab.traces.has_results

    def assert_traffic(self, name, traffic_tab, self_object_type, traffic_object_type):
        inbound_traffic = traffic_tab.inbound_items()
        for inbound_item in inbound_traffic:
            if inbound_item.object_type == traffic_object_type:
                # skip istio traffic
                if "istio" in inbound_item.name:
                    continue
                outbound_traffic = traffic_tab.click_on(
                    object_type=traffic_object_type, name=inbound_item.name, inbound=True)
                found = False
                for outbound_item in outbound_traffic:
                    if (outbound_item.name == name
                        and outbound_item.object_type == self_object_type
                            and outbound_item.request_type == inbound_item.request_type):
                        # TODO check traffic
                        found = True
                if not found:
                    assert found, "{} {} {} not found in {}".format(name,
                                                                    self_object_type,
                                                                    inbound_item.request_type,
                                                                    outbound_traffic)
                # check only the first item
                break


class OverviewPageTest(AbstractListPageTest):
    FILTER_ENUM = OverviewPageFilter
    TYPE_ENUM = OverviewPageType
    SORT_ENUM = OverviewPageSort

    def _namespaces_ui(self):
        return self.page.filter.filter_options(filter_name=self.FILTER_ENUM.NAME.text)

    def __init__(self, kiali_client, openshift_client, browser):
        AbstractListPageTest.__init__(
            self, kiali_client=kiali_client,
            openshift_client=openshift_client, page=OverviewPage(browser))
        self.browser = browser

    def assert_type_options(self):
        # test available type options
        options_defined = [item.text for item in self.TYPE_ENUM]
        options_listed = self.page.type.options
        logger.debug('Options[defined:{}, defined:{}]'.format(options_defined, options_listed))
        assert is_equal(options_defined, options_listed)

    def assert_all_items(self, filters=[],
                         overview_type=TYPE_ENUM.APPS, force_clear_all=True,
                         force_refresh=False):
        # apply overview type
        self.page.type.select(overview_type.text)

        # apply filters
        self.apply_filters(filters=filters, force_clear_all=force_clear_all)

        if force_refresh:
            self.page.page_refresh()
        # get overviews from ui
        overviews_ui = self.page.content.all_items
        # get overviews from rest api
        _ns = self.FILTER_ENUM.NAME.text
        _namespaces = [_f['value'] for _f in filters if _f['name'] == _ns]
        logger.debug('Namespaces:{}'.format(_namespaces))
        overviews_rest = self.kiali_client.overview_list(
            namespaces=_namespaces,
            overview_type=overview_type)

        # compare all results
        logger.debug('Namespaces:{}'.format(_namespaces))
        logger.debug('Items count[UI:{}, REST:{}]'.format(
            len(overviews_ui), len(overviews_rest)))
        logger.debug('overviews UI:{}'.format(overviews_ui))
        logger.debug('overviews REST:{}'.format(overviews_rest))

        assert len(overviews_ui) == len(overviews_rest)

        for overview_ui in overviews_ui:
            found = False
            for overview_rest in overviews_rest:
                if overview_ui.is_equal(overview_rest, advanced_check=False):
                    found = True
                    break
            assert found, '{} not found in REST {}'.format(overview_ui, overviews_rest)


class ApplicationsPageTest(AbstractListPageTest):
    FILTER_ENUM = ApplicationsPageFilter
    SORT_ENUM = ApplicationsPageSort

    def __init__(self, kiali_client, openshift_client, browser):
        AbstractListPageTest.__init__(
            self, kiali_client=kiali_client,
            openshift_client=openshift_client, page=ApplicationsPage(browser))
        self.browser = browser

    def _prepare_load_details_page(self, name, namespace):
        # load the page first
        self.page.load(force_load=True)
        # apply namespace
        self.apply_namespaces(namespaces=[namespace])
        # apply filters
        self.apply_filters(filters=[
            {'name': ApplicationsPageFilter.APP_NAME.text, 'value': name}])

    def load_details_page(self, name, namespace, force_refresh, load_only=False):
        if not self.is_in_details_page(name, namespace):
            self._prepare_load_details_page(name, namespace)
            self.open(name, namespace, force_refresh)
        return self.page.content.get_details(load_only)

    def assert_random_details(self, namespaces=[], filters=[], force_refresh=False):
        # get applications from rest api
        _sn = self.FILTER_ENUM.APP_NAME.text
        _application_names = [_f['value'] for _f in filters if _f['name'] == _sn]
        logger.debug('Namespaces:{}, Application names:{}'.format(namespaces, _application_names))
        applications_rest = self.kiali_client.application_list(
            namespaces=namespaces, application_names=_application_names)

        # random applications filters
        assert len(applications_rest) > 0
        if len(applications_rest) > 3:
            _random_applications = random.sample(applications_rest, 3)
        else:
            _random_applications = applications_rest
        # create filters
        for _idx, _selected_application in enumerate(_random_applications):
            self.assert_details(
                _selected_application.name,
                _selected_application.namespace,
                check_metrics=True if _idx == 0 else False,
                force_refresh=force_refresh)

    def assert_details(self, name, namespace, check_metrics=False, force_refresh=False):
        logger.debug('Details: {}, {}'.format(name, namespace))

        # load application details page
        application_details_ui = self.load_details_page(name, namespace, force_refresh)
        assert application_details_ui
        assert name == application_details_ui.name
        # get application detals from rest
        application_details_rest = self.kiali_client.application_details(
            namespace=namespace,
            application_name=name)
        assert application_details_rest
        assert name == application_details_rest.name
        application_details_oc = self.openshift_client.application_details(
            namespace=namespace,
            application_name=name)
        assert application_details_oc

        assert application_details_ui.is_equal(application_details_rest,
                                               advanced_check=True), \
            'Application UI {} not equal to REST {}'\
            .format(application_details_ui, application_details_rest)
        for workload_ui in application_details_ui.workloads:
            found = False
            for workload_rest in application_details_rest.workloads:
                if workload_ui.is_equal(workload_rest,
                                        advanced_check=True):
                    found = True
                    break
            if not found:
                assert found, 'Workload {} not found in REST {}'.format(workload_ui, workload_rest)
            found = False
            for workload_oc in application_details_oc.workloads:
                if workload_ui.is_equal(workload_oc,
                                        advanced_check=False):
                    found = True
                    break
            if not found:
                assert found, 'Workload {} not found in OC {}'.format(workload_ui, workload_oc)
        assert application_details_ui.services == application_details_rest.services, \
            'UI services {} not equal to REST {}'.format(
                application_details_ui.services,
                application_details_rest.services)
        assert is_equal(application_details_ui.services, application_details_oc.services), \
            'UI services {} not equal to OC {}'.format(
                application_details_ui.services,
                application_details_oc.services)

        if check_metrics:
            self.assert_metrics_options(application_details_ui.inbound_metrics)

            self.assert_metrics_options(application_details_ui.outbound_metrics)
        self.assert_traffic(name, application_details_ui.traffic_tab,
                            self_object_type=TrafficType.APP, traffic_object_type=TrafficType.APP)

    def assert_all_items(self, namespaces=[], filters=[], sort_options=[], force_clear_all=True):
        # apply namespaces
        self.apply_namespaces(namespaces, force_clear_all=force_clear_all)

        # apply filters
        self.apply_filters(filters=filters, force_clear_all=force_clear_all)

        # apply sorting
        self.sort(sort_options)

        # get applications from rest api
        _sn = self.FILTER_ENUM.APP_NAME.text
        _application_names = [_f['value'] for _f in filters if _f['name'] == _sn]

        logger.debug('Namespaces:{}, Application names:{}'.format(namespaces, _application_names))
        # get applications from ui
        applications_ui = self.page.content.all_items
        # get from REST
        applications_rest = self.kiali_client.application_list(
            namespaces=namespaces, application_names=_application_names)
        # get from OC
        applications_oc = self.openshift_client.application_list(
            namespaces=namespaces, application_names=_application_names)

        # compare all results
        logger.debug('Namespaces:{}, Service names:{}'.format(namespaces, _application_names))
        logger.debug('Items count[UI:{}, REST:{}]'.format(
            len(applications_ui), len(applications_rest)))
        logger.debug('Applications UI:{}'.format(applications_ui))
        logger.debug('Applications REST:{}'.format(applications_rest))
        logger.debug('Applications OC:{}'.format(applications_oc))

        assert len(applications_ui) == len(applications_rest), \
            "UI {} and REST {} applications number not equal".format(applications_ui,
                                                                     applications_ui)
        assert len(applications_rest) <= len(applications_oc)

        for application_ui in applications_ui:
            found = False
            for application_rest in applications_rest:
                if application_ui.is_equal(application_rest, advanced_check=True):
                    found = True
                    break
            if not found:
                assert found, '{} not found in REST'.format(application_ui)
            found = False
            for application_oc in applications_oc:
                logger.debug('{} {}'.format(application_oc.name, application_oc.namespace))
                if application_ui.is_equal(application_oc, advanced_check=False):
                    found = True
                    break
            if not found:
                assert found, '{} not found in OC'.format(application_ui)


class WorkloadsPageTest(AbstractListPageTest):
    FILTER_ENUM = WorkloadsPageFilter
    SORT_ENUM = WorkloadsPageSort

    def __init__(self, kiali_client, openshift_client, browser):
        AbstractListPageTest.__init__(
            self, kiali_client=kiali_client,
            openshift_client=openshift_client, page=WorkloadsPage(browser))
        self.browser = browser

    def _prepare_load_details_page(self, name, namespace):
        # load the page first
        self.page.load(force_load=True)
        # apply namespace
        self.apply_namespaces(namespaces=[namespace])
        # apply filters
        self.apply_filters(filters=[
            {'name': WorkloadsPageFilter.WORKLOAD_NAME.text, 'value': name}])

    def load_details_page(self, name, namespace, force_refresh, load_only=False):
        if not self.is_in_details_page(name, namespace):
            self._prepare_load_details_page(name, namespace)
            self.open(name, namespace, force_refresh)
        return self.page.content.get_details(load_only)

    def assert_random_details(self, namespaces=[], filters=[],
                              force_clear_all=True, force_refresh=False):
        # get workloads from rest api
        _sn = self.FILTER_ENUM.WORKLOAD_NAME.text
        _workload_names = [_f['value'] for _f in filters if _f['name'] == _sn]
        logger.debug('Namespaces:{}, Workload names:{}'.format(namespaces, _workload_names))
        workloads_rest = self.kiali_client.workload_list(
            namespaces=namespaces, workload_names=_workload_names)
        # random workloads filters
        assert len(workloads_rest) > 0
        if len(workloads_rest) > 3:
            _random_workloads = random.sample(workloads_rest, 3)
        else:
            _random_workloads = workloads_rest
        # create filters
        for _idx, _selected_workload in enumerate(_random_workloads):
            self.assert_details(_selected_workload.name,
                                _selected_workload.namespace,
                                _selected_workload.workload_type,
                                True if _idx == 0 else False,
                                force_refresh=force_refresh)

    def assert_details(self, name, namespace, workload_type, check_metrics=False,
                       force_refresh=False):
        logger.debug('Details: {}, {}'.format(name, namespace))

        # load workload details page
        workload_details_ui = self.load_details_page(name, namespace, force_refresh)
        assert workload_details_ui
        assert name == workload_details_ui.name
        assert workload_type == workload_details_ui.workload_type, \
            '{} and {} are not equal'.format(workload_type, workload_details_ui.workload_type)
        # get workload detals from rest
        workload_details_rest = self.kiali_client.workload_details(
            namespace=namespace,
            workload_name=name,
            workload_type=workload_type)
        assert workload_details_rest
        assert name == workload_details_rest.name
        # get workload detals from rest
        workload_details_oc = self.openshift_client.workload_details(
            namespace=namespace,
            workload_name=name,
            workload_type=workload_type)
        assert workload_details_oc
        assert name == workload_details_oc.name

        assert workload_details_ui.is_equal(workload_details_rest,
                                            advanced_check=True), \
            'Workload UI {} not equal to REST {}'\
            .format(workload_details_ui, workload_details_rest)
        assert workload_details_ui.is_equal(workload_details_oc,
                                            advanced_check=False), \
            'Workload UI {} not equal to OC {}'\
            .format(workload_details_ui, workload_details_oc)
        if workload_details_ui.pods_number != workload_details_rest.pods_number:
            return False
        if workload_details_ui.services_number != workload_details_rest.services_number:
            return False
        # if workload_details_ui.destination_services_number \
        #         != workload_details_rest.destination_services_number:
        #     return False
        for pod_ui in workload_details_ui.pods:
            found = False
            for pod_rest in workload_details_rest.pods:
                if pod_ui.is_equal(pod_rest,
                                   advanced_check=True):
                    found = True
                    break
            if not found:
                assert found, 'Pod {} not found in REST {}'.format(pod_ui, pod_rest)
        for service_ui in workload_details_ui.services:
            found = False
            for service_rest in workload_details_rest.services:
                if service_ui.is_equal(service_rest,
                                       advanced_check=True):
                    found = True
                    break
            if not found:
                assert found, 'Service {} not found in REST {}'.format(service_ui, service_rest)

        if check_metrics:
            self.assert_metrics_options(workload_details_ui.inbound_metrics)

            self.assert_metrics_options(workload_details_ui.outbound_metrics)
        self.assert_traffic(name, workload_details_ui.traffic_tab,
                            self_object_type=TrafficType.WORKLOAD,
                            traffic_object_type=TrafficType.SERVICE)

    def assert_all_items(self, namespaces=[], filters=[], sort_options=[], force_clear_all=True):
        # apply namespaces
        self.apply_namespaces(namespaces, force_clear_all=force_clear_all)

        # apply filters
        self.apply_filters(filters=filters, force_clear_all=force_clear_all)

        # apply sorting
        self.sort(sort_options)

        # get workloads from ui
        workloads_ui = self.page.content.all_items
        # get workloads from rest api
        _sn = self.FILTER_ENUM.WORKLOAD_NAME.text
        _workload_names = [_f['value'] for _f in filters if _f['name'] == _sn]
        logger.debug('Namespaces:{}, Workload names:{}'.format(namespaces, _workload_names))
        workloads_rest = self.kiali_client.workload_list(
            namespaces=namespaces, workload_names=_workload_names)
        # get workloads from OC client
        workloads_oc = self.openshift_client.workload_list(
            namespaces=namespaces, workload_names=_workload_names)

        # compare all results
        logger.debug('Namespaces:{}, Service names:{}'.format(namespaces, _workload_names))
        logger.debug('Items count[UI:{}, REST:{}, OC:{}]'.format(
            len(workloads_ui), len(workloads_rest), len(workloads_oc)))
        logger.debug('Workloads UI:{}'.format(workloads_ui))
        logger.debug('Workloads REST:{}'.format(workloads_rest))
        logger.debug('Workloads OC:{}'.format(workloads_oc))

        assert len(workloads_ui) == len(workloads_rest), \
            "UI {} and REST {} workloads number not equal".format(workloads_ui, workloads_rest)
        # TODO when workloads are filtered put == here
        assert len(workloads_rest) <= len(workloads_oc)

        for workload_ui in workloads_ui:
            found = False
            for workload_rest in workloads_rest:
                if workload_ui.is_equal(workload_rest, advanced_check=True):
                    found = True
                    break
            if not found:
                assert found, '{} not found in REST'.format(workload_ui)
            found = False
            for workload_oc in workloads_oc:
                if workload_ui.is_equal(workload_oc, advanced_check=False):
                    found = True
                    break
            if not found:
                assert found, '{} not found in OC'.format(workload_ui)


class ServicesPageTest(AbstractListPageTest):
    FILTER_ENUM = ServicesPageFilter
    SORT_ENUM = ServicesPageSort

    def __init__(self, kiali_client, openshift_client, browser):
        AbstractListPageTest.__init__(
            self, kiali_client=kiali_client,
            openshift_client=openshift_client, page=ServicesPage(browser))
        self.browser = browser

    def _prepare_load_details_page(self, name, namespace):
        # load the page first
        self.page.load(force_load=True)
        # apply namespace
        self.apply_namespaces(namespaces=[namespace])
        # apply filters
        self.apply_filters(filters=[
            {'name': ServicesPageFilter.SERVICE_NAME.text, 'value': name}])

    def load_details_page(self, name, namespace, force_refresh, load_only=False):
        if not self.is_in_details_page(name, namespace):
            self._prepare_load_details_page(name, namespace)
            self.open(name, namespace, force_refresh)
        return self.page.content.get_details(load_only)

    def assert_random_details(self, namespaces=[], filters=[], force_refresh=False):
        # get services from rest api
        _sn = self.FILTER_ENUM.SERVICE_NAME.text
        _service_names = [_f['value'] for _f in filters if _f['name'] == _sn]
        logger.debug('Namespaces:{}, Service names:{}'.format(namespaces, _service_names))
        services_rest = self.kiali_client.service_list(
            namespaces=namespaces, service_names=_service_names)
        # random services filters
        assert len(services_rest) > 0
        if len(services_rest) > 2:
            _random_services = random.sample(services_rest, 2)
        else:
            _random_services = services_rest
        # create filters
        for _idx, _selected_service in enumerate(_random_services):
            self.assert_details(_selected_service.name, _selected_service.namespace,
                                check_metrics=True if _idx == 0 else False,
                                force_refresh=force_refresh)

    def assert_details(self, name, namespace, check_metrics=False,
                       force_refresh=False):
        logger.debug('Details: {}, {}'.format(name, namespace))
        # load service details page
        service_details_ui = self.load_details_page(name, namespace, force_refresh)
        assert service_details_ui
        assert name == service_details_ui.name
        # get service details from rest
        service_details_rest = self.kiali_client.service_details(
            namespace=namespace,
            service_name=name)
        assert service_details_rest
        assert name == service_details_rest.name
        service_details_oc = self.openshift_client.service_details(namespace=namespace,
                                                                   service_name=name)
        assert service_details_oc
        assert name == service_details_oc.name

        assert service_details_rest.istio_sidecar\
            == service_details_ui.istio_sidecar
        assert service_details_ui.is_equal(service_details_rest,
                                           advanced_check=True), \
            'Service UI {} not equal to REST {}'\
            .format(service_details_ui, service_details_rest)
        assert service_details_ui.is_equal(service_details_oc,
                                           advanced_check=False), \
            'Service UI {} not equal to OC {}'\
            .format(service_details_ui, service_details_oc)
        assert service_details_ui.workloads_number\
            == len(service_details_rest.workloads)
        assert service_details_ui.virtual_services_number\
            == len(service_details_rest.virtual_services)
        assert service_details_ui.destination_rules_number\
            == len(service_details_rest.destination_rules)
        assert service_details_ui.workloads_number\
            == len(service_details_rest.workloads)
        assert service_details_ui.virtual_services_number\
            == len(service_details_ui.virtual_services)
        assert service_details_ui.destination_rules_number\
            == len(service_details_ui.destination_rules)

        for workload_ui in service_details_ui.workloads:
            found = False
            for workload_rest in service_details_rest.workloads:
                if workload_ui.is_equal(workload_rest, advanced_check=True):
                    found = True
                    break
            assert found, 'Workload {} not found in REST {}'.format(workload_ui,
                                                                    workload_rest)
        for virtual_service_ui in service_details_ui.virtual_services:
            found = False
            for virtual_service_rest in service_details_rest.virtual_services:
                if virtual_service_ui.is_equal(virtual_service_rest, advanced_check=False):
                    found = True
                    break
            if not found:
                assert found, 'VS {} not found in REST {}'.format(virtual_service_ui,
                                                                  virtual_service_rest)
            vs_overview = self.page.content.table_view_vs.get_overview(virtual_service_ui.name)
            assert vs_overview.is_equal(virtual_service_rest, advanced_check=True)

        for destination_rule_ui in service_details_ui.destination_rules:
            found = False
            for destination_rule_rest in service_details_rest.destination_rules:
                if destination_rule_ui.is_equal(destination_rule_rest, advanced_check=True):
                    found = True
                    break
            if not found:
                assert found, 'DR {} not found in REST {}'.format(destination_rule_ui,
                                                                  destination_rule_rest)
            dr_overview = self.page.content.table_view_dr.get_overview(destination_rule_ui.name)
            # TODO advanced_check=True when KIALI-2152 is done
            assert dr_overview.is_equal(destination_rule_ui, advanced_check=False)

        if check_metrics:
            self.assert_metrics_options(service_details_ui.inbound_metrics)
        # TODO KIALI-3262
        # self.assert_traces_tab(service_details_ui.traces_tab)
        # service traffic is linked to workloads
        self.assert_traffic(name, service_details_ui.traffic_tab,
                            self_object_type=TrafficType.SERVICE,
                            traffic_object_type=TrafficType.WORKLOAD)

    def get_workload_names_set(self, source_workloads):
        workload_names = []
        for source_workload in source_workloads:
            for workload in source_workload.workloads:
                workload_names.append(workload)
        return set(workload_names)

    def assert_all_items(self, namespaces=[], filters=[], sort_options=[], force_clear_all=True):
        # apply namespaces
        self.apply_namespaces(namespaces, force_clear_all=force_clear_all)

        # apply filters
        self.apply_filters(filters=filters, force_clear_all=force_clear_all)

        # apply sorting
        self.sort(sort_options)

        # get services from ui
        services_ui = self.page.content.all_items
        # get services from rest api
        _sn = self.FILTER_ENUM.SERVICE_NAME.text
        _service_names = [_f['value'] for _f in filters if _f['name'] == _sn]
        logger.debug('Namespaces:{}, Service names:{}'.format(namespaces, _service_names))
        services_rest = self.kiali_client.service_list(
            namespaces=namespaces, service_names=_service_names)
        # get services from OC client
        services_oc = self.openshift_client.service_list(
            namespaces=namespaces, service_names=_service_names)

        # compare all results
        logger.debug('Namespaces:{}, Service names:{}'.format(namespaces, _service_names))
        logger.debug('Items count[UI:{}, REST:{}, OC:{}]'.format(
            len(services_ui), len(services_rest), len(services_oc)))
        logger.debug('Services UI:{}'.format(services_ui))
        logger.debug('Services REST:{}'.format(services_rest))
        logger.debug('Services OC:{}'.format(services_oc))

        assert len(services_ui) == len(services_rest), \
            "UI {} and REST {} services number not equal".format(services_ui, services_rest)
        assert len(services_rest) <= len(services_oc)

        for service_ui in services_ui:
            found = False
            for service_rest in services_rest:
                if service_ui.is_equal(service_rest, advanced_check=True):
                    found = True
                    break
            if not found:
                assert found, '{} not found in REST'.format(service_ui)
            found = False
            for service_oc in services_oc:
                if service_ui.is_equal(service_oc, advanced_check=False):
                    found = True
                    break
            if not found:
                assert found, '{} not found in OC'.format(service_ui)

    def get_additional_filters(self, namespaces, current_filters):
        logger.debug('Current filters:{}'.format(current_filters))
        # get services of a namespace
        _namespace = namespaces[0]
        logger.debug('Running Services REST query for namespace:{}'.format(_namespace))
        _services = self.kiali_client.service_list(namespaces=[_namespace])
        logger.debug('Query response, Namespace:{}, Services:{}'.format(_namespace, _services))
        # if we have a service, select a service randomly and return it
        if len(_services) > 0:
            _random_service = random.choice(_services)
            return [
                {
                    'name': self.FILTER_ENUM.SERVICE_NAME.text,
                    'value': _random_service.name
                }
            ]
        return []

    def test_routing_create(self, name, namespace, routing_type,
                            tls=RoutingWizardTLS.ISTIO_MUTUAL, load_balancer=True,
                            load_balancer_type=RoutingWizardLoadBalancer.ROUND_ROBIN,
                            gateway=True, include_mesh_gateway=True):
        logger.debug('Routing Wizard {} for Service: {}, {}'.format(routing_type, name, namespace))
        # load service details page
        self._prepare_load_details_page(name, namespace)
        self.open(name, namespace)
        self.page.actions.delete_all_routing()
        if routing_type == RoutingWizardType.CREATE_WEIGHTED_ROUTING:
            assert self.page.actions.create_weighted_routing(
                tls=tls, load_balancer=load_balancer,
                load_balancer_type=load_balancer_type, gateway=gateway,
                include_mesh_gateway=include_mesh_gateway)
            assert not self.page.actions.is_delete_disabled()
            assert self.page.actions.is_update_weighted_enabled()
            assert self.page.actions.is_create_matching_disabled()
            assert self.page.actions.is_suspend_disabled()
        elif routing_type == RoutingWizardType.CREATE_MATCHING_ROUTING:
            assert self.page.actions.create_matching_routing(
                tls=tls, load_balancer=load_balancer,
                load_balancer_type=load_balancer_type, gateway=gateway,
                include_mesh_gateway=include_mesh_gateway)
            assert not self.page.actions.is_delete_disabled()
            assert self.page.actions.is_update_matching_enabled()
            assert self.page.actions.is_create_weighted_disabled()
            assert self.page.actions.is_suspend_disabled()
        elif routing_type == RoutingWizardType.SUSPEND_TRAFFIC:
            assert self.page.actions.suspend_traffic(
                tls=tls, load_balancer=load_balancer,
                load_balancer_type=load_balancer_type, gateway=gateway,
                include_mesh_gateway=include_mesh_gateway)
            assert not self.page.actions.is_delete_disabled()
            assert self.page.actions.is_create_matching_disabled()
            assert self.page.actions.is_create_weighted_disabled()
            assert self.page.actions.is_update_suspended_enabled()
        # get service details from rest
        service_details_rest = self.kiali_client.service_details(
            namespace=namespace,
            service_name=name)
        assert len(service_details_rest.virtual_services) == 1, 'Service should have 1 VS'
        assert len(service_details_rest.destination_rules) == 1, 'Service should have 1 DR'
        assert service_details_rest.virtual_services[0].name == name
        assert service_details_rest.destination_rules[0].name == name

        if load_balancer_type:
            assert word_in_text(load_balancer_type.text.lower(),
                                service_details_rest.destination_rules[0].traffic_policy,
                                load_balancer)

        if tls:
            assert word_in_text(tls.text.lower(),
                                service_details_rest.destination_rules[0].traffic_policy,
                                tls)
        # get virtual service details from rest
        istio_config_details_rest = self.kiali_client.istio_config_details(
            namespace=namespace,
            object_type=OBJECT_TYPE.VIRTUAL_SERVICE.text,
            object_name=service_details_rest.virtual_services[0].name)

        assert word_in_text('\"mesh\"',
                            istio_config_details_rest.text,
                            gateway and include_mesh_gateway)

    def test_routing_update(self, name, namespace, routing_type,
                            tls=RoutingWizardTLS.ISTIO_MUTUAL, load_balancer=True,
                            load_balancer_type=RoutingWizardLoadBalancer.ROUND_ROBIN,
                            gateway=True, include_mesh_gateway=True):
        logger.debug('Routing Update Wizard {} for Service: {}, {}'.format(routing_type,
                                                                           name,
                                                                           namespace))
        # load service details page
        self._prepare_load_details_page(name, namespace)
        self.open(name, namespace)
        if routing_type == RoutingWizardType.UPDATE_WEIGHTED_ROUTING:
            assert self.page.actions.update_weighted_routing(
                tls=tls, load_balancer=load_balancer,
                load_balancer_type=load_balancer_type, gateway=gateway,
                include_mesh_gateway=include_mesh_gateway)
            assert not self.page.actions.is_delete_disabled()
            assert self.page.actions.is_update_weighted_enabled()
            assert self.page.actions.is_create_matching_disabled()
            assert self.page.actions.is_suspend_disabled()
        elif routing_type == RoutingWizardType.UPDATE_MATCHING_ROUTING:
            assert self.page.actions.update_matching_routing(
                tls=tls, load_balancer=load_balancer,
                load_balancer_type=load_balancer_type, gateway=gateway,
                include_mesh_gateway=include_mesh_gateway)
            assert not self.page.actions.is_delete_disabled()
            assert self.page.actions.is_update_matching_enabled()
            assert self.page.actions.is_create_weighted_disabled()
            assert self.page.actions.is_suspend_disabled()
        elif routing_type == RoutingWizardType.UPDATE_SUSPENDED_TRAFFIC:
            assert self.page.actions.update_suspended_traffic(
                tls=tls, load_balancer=load_balancer,
                load_balancer_type=load_balancer_type, gateway=gateway,
                include_mesh_gateway=include_mesh_gateway)
            assert not self.page.actions.is_delete_disabled()
            assert self.page.actions.is_create_matching_disabled()
            assert self.page.actions.is_create_weighted_disabled()
            assert self.page.actions.is_update_suspended_enabled()
        # get service details from rest
        service_details_rest = self.kiali_client.service_details(
            namespace=namespace,
            service_name=name)
        assert len(service_details_rest.virtual_services) == 1, 'Service should have 1 VS'
        assert len(service_details_rest.destination_rules) == 1, 'Service should have 1 DR'
        assert service_details_rest.virtual_services[0].name == name
        assert service_details_rest.destination_rules[0].name == name

        if load_balancer_type:
            assert word_in_text(load_balancer_type.text.lower(),
                                service_details_rest.destination_rules[0].traffic_policy,
                                load_balancer)

        if tls:
            assert word_in_text(tls.text.lower(),
                                service_details_rest.destination_rules[0].traffic_policy,
                                tls)
        # get virtual service details from rest
        istio_config_details_rest = self.kiali_client.istio_config_details(
            namespace=namespace,
            object_type=OBJECT_TYPE.VIRTUAL_SERVICE.text,
            object_name=service_details_rest.virtual_services[0].name)

        assert word_in_text('\"mesh\"',
                            istio_config_details_rest.text,
                            gateway and include_mesh_gateway)

    def test_routing_delete(self, name, namespace):
        logger.debug('Routing Delete for Service: {}, {}'.format(name, namespace))
        # load service details page
        self._prepare_load_details_page(name, namespace)
        self.open(name, namespace)
        assert self.page.actions.delete_all_routing()
        assert self.page.actions.is_delete_disabled()
        assert self.page.actions.is_create_weighted_enabled()
        assert self.page.actions.is_create_matching_enabled()
        assert self.page.actions.is_suspend_enabled()
        # get service details from rest
        service_details_rest = self.kiali_client.service_details(
            namespace=namespace,
            service_name=name)
        assert len(service_details_rest.virtual_services) == 0, 'Service should have no VS'
        assert len(service_details_rest.destination_rules) == 0, 'Service should have no DR'


class IstioConfigPageTest(AbstractListPageTest):
    FILTER_ENUM = IstioConfigPageFilter
    SORT_ENUM = IstioConfigPageSort

    def __init__(self, kiali_client, openshift_client, browser):
        AbstractListPageTest.__init__(
            self, kiali_client=kiali_client,
            openshift_client=openshift_client, page=IstioConfigPage(browser))
        self.browser = browser

    def _prepare_load_details_page(self, name, namespace):
        # load the page first
        self.page.load(force_load=True)
        # apply namespace
        self.apply_namespaces(namespaces=[namespace])
        # apply filters
        self.apply_filters(filters=[
            {'name': IstioConfigPageFilter.ISTIO_NAME.text, 'value': name}])

    def load_details_page(self, name, namespace, force_refresh, load_only=False):
        if not self.is_in_details_page(name, namespace):
            self._prepare_load_details_page(name, namespace)
            self.open(name, namespace, force_refresh)
        return self.page.content.get_details(name, load_only)

    def assert_all_items(self, namespaces=[], filters=[], sort_options=[], force_clear_all=True):
        logger.debug('Filters:{}'.format(filters))

        # apply namespaces
        self.apply_namespaces(namespaces, force_clear_all=force_clear_all)

        # apply filters
        self.apply_filters(filters=filters, force_clear_all=force_clear_all)

        # apply sorting
        self.sort(sort_options)

        _sn = self.FILTER_ENUM.ISTIO_NAME.text
        _istio_names = [_f['value'] for _f in filters if _f['name'] == _sn]

        # get rules from ui
        config_list_ui = self.page.content.all_items
        logger.debug('Istio config list UI:{}]'.format(config_list_ui))

        # get rules from rest api
        config_list_rest = self.kiali_client.istio_config_list(
            namespaces=namespaces, config_names=_istio_names)
        logger.debug('Istio config list REST:{}]'.format(config_list_rest))

        # get configs from OC api
        config_list_oc = self.openshift_client.istio_config_list(
            namespaces=namespaces, config_names=_istio_names)
        logger.debug('Istio config list OC API:{}]'.format(config_list_oc))

        # compare 3 way results
        assert len(config_list_ui) == len(config_list_rest), \
            "UI {} and REST {} config number not equal".format(config_list_ui, config_list_rest)
        assert len(config_list_ui) == len(config_list_oc)
        for config_ui in config_list_ui:
            found = False
            for config_rest in config_list_rest:
                if config_ui.is_equal(config_rest, advanced_check=True):
                    found = True
                    break
            if not found:
                assert found, '{} not found in REST'.format(config_ui)
            found = False
            for config_oc in config_list_oc:
                if config_ui.is_equal(config_oc, advanced_check=False):
                    found = True
                    break
            if not found:
                assert found, '{} not found in OC'.format(config_ui)

    def assert_random_details(self, namespaces=[], filters=[]):
        # get istio config from rest api
        configs_rest = self.kiali_client.istio_config_list(namespaces, filters)

        # random configs filters
        assert len(configs_rest) > 0
        if len(configs_rest) > 3:
            _random_configs = random.sample(configs_rest, 3)
        else:
            _random_configs = configs_rest
        # create filters
        for _selected_config in _random_configs:
            if _selected_config.object_type != OBJECT_TYPE.RULE.text:
                self.assert_details(_selected_config.name,
                                    _selected_config.object_type,
                                    _selected_config.namespace)

    def assert_details(self, name, object_type,
                       namespace=None, error_messages=[], apply_filters=True):
        logger.debug('Details: {}, {}'.format(name, namespace))

        # load config details page
        config_details_ui = self.load_details_page(name, namespace, force_refresh=False)
        assert config_details_ui
        assert name == config_details_ui.name
        assert config_details_ui.text
        # get config details from rest
        config_details_rest = self.kiali_client.istio_config_details(
            namespace=namespace,
            object_type=object_type,
            object_name=name)
        assert config_details_rest
        assert name == config_details_rest.name
        assert config_details_rest.text
        # get config details from OC
        config_details_oc = self.openshift_client.istio_config_details(
            namespace=namespace,
            object_name=name,
            object_type=object_type)
        assert config_details_oc
        assert name == config_details_oc.name
        for error_message in error_messages:
            assert error_message in config_details_rest.error_messages, \
                'Error messages:{} is not in List:{}'.format(error_message,
                                                             config_details_rest.error_messages)
        # TODO for Gateways there is no way to check in UI if it is valid or N/A
        assert config_details_ui.is_equal(
            config_details_rest,
            advanced_check=True if
            config_details_rest.validation != IstioConfigValidation.NA
            else False)
        # find key: value pairs from UI in a REST
        for config_ui in re.split(' ',
                                  str(config_details_ui.text).
                                  replace('\'', '').
                                  replace('~', 'null').
                                  replace('selfLink: >- ', 'selfLink: ').
                                  replace(': > ', ': ').
                                  replace('{', '').
                                  replace('}', '').
                                  replace('"', '').
                                  replace(',', '').
                                  replace('[', '').
                                  replace(']', '').
                                  replace('\\', '')):
            if config_ui.endswith(':'):
                ui_key = config_ui
            elif config_ui.strip() != '-':  # skip this line, it was for formatting
                # the previous one was the key of this value
                found = False
                # make the REST result into the same format as shown in UI
                # to compare only the values
                for config_rest in str(config_details_rest.text).\
                        replace('\\n', '').\
                        replace('\\', '').\
                        replace('{', '').\
                        replace('}', '').\
                        replace('"', '').\
                        replace(',', '').\
                        replace('[', '').\
                        replace(']', '').\
                        split(' '):
                    if config_rest.endswith(':'):
                        rest_key = config_rest
                    else:
                        # the previous one was the key of this value
                        if ui_key == rest_key and config_ui == config_rest:
                            found = True
                            break
                if not found:
                    assert found, '{} {} not found in REST'.format(ui_key, config_ui)
                found = False
                # make the OC result into the same format as shown in UI
                # to compare only the values
                config_oc_list = str(config_details_oc.text).\
                    replace('\n', '').\
                    replace('\'', '').\
                    replace("\\n", '').\
                    replace(' - ', '').\
                    replace('{', '').\
                    replace('}', '').\
                    replace('"', '').\
                    replace(',', '').\
                    replace('[', '').\
                    replace(']', '').\
                    split(' ')
                config_oc_list.append('kind:')
                config_oc_list.append(config_details_oc._type)
                if ui_key == 'apiVersion:':
                    continue
                for config_oc in config_oc_list:
                    if config_oc.endswith(':'):
                        oc_key = config_oc
                    else:
                        # the previous one was the key of this value
                        if (ui_key == oc_key and config_ui == config_oc) or config_ui == 'null':
                            found = True
                            break
                if not found:
                    assert found, '{} {} not found in OC'.format(ui_key, config_ui)

    def delete_istio_config(self, name, namespace=None):
        self.load_details_page(name, namespace, force_refresh=False, load_only=True)
        self.page.actions.select('Delete')
        wait_displayed(self.page.content)
        self.browser.click(self.browser.element(
            parent=ListViewAbstract.DIALOG_ROOT,
            locator=('.//button[text()="Delete"]')))
        wait_displayed(self.page.content)

    def click_on_gateway(self, name, namespace):
        self.browser.click(self.browser.element(locator=self.page.content.CONFIG_TAB_OVERVIEW,
                                                parent=self.page.content.CONFIG_TABS_PARENT))
        self.browser.click(
            './/a[contains(@href, "/namespaces/{}/istio/gateways/{}")]'.format(namespace, name),
            parent=self.page.content.locator)

    def get_additional_filters(self, namespaces, current_filters):
        logger.debug('Current filters:{}'.format(current_filters))
        # get rules of a namespace
        _namespace = namespaces[0]
        logger.debug('Running Rules REST query for namespace:{}'.format(_namespace))
        _istio_config_list = self.kiali_client.istio_config_list(
            namespaces=[_namespace])
        logger.debug('Query response, Namespace:{}, Istio config list:{}'.format(
            _namespace, _istio_config_list))
        # if we have a config, select a config randomly and return it
        if len(_istio_config_list) > 0:
            _random_config = random.choice(_istio_config_list)
            return [
                {
                    'name': self.FILTER_ENUM.ISTIO_NAME.text,
                    'value': _random_config.name
                }
            ]
        return []


class DistributedTracingPageTest(AbstractListPageTest):

    def load_page(self, namespaces, force_clear_all):
        self.page.load(force_load=True)
        # apply namespaces
        self.apply_namespaces(namespaces, force_clear_all=force_clear_all)

    def __init__(self, kiali_client, openshift_client, browser):
        AbstractListPageTest.__init__(
            self, kiali_client=kiali_client,
            openshift_client=openshift_client, page=DistributedTracingPage(browser))
        self.browser = browser

    def assert_search_traces(self, service_name, namespaces=[], force_clear_all=True):
        # test Search Traces for provided Namespace and Service
        self.load_page(namespaces, force_clear_all)
        self.page.traces.search_traces(service_name)
        assert not self.page.traces.is_oc_login_displayed, "OC Login should not be displayed"
        if not self.page.traces.has_no_results:
            assert self.page.traces.has_results
