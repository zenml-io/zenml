from zenml.standards.standard_keys import MethodKeys


def parse_methods(input_dict, process, methods):
    """
    Args:
        input_dict:
        process:
        methods:
    """
    result = {}

    # Obtain the set of features
    f_set = set(input_dict.keys())
    f_list = list(sorted(f_set))

    for feature in f_list:
        assert isinstance(input_dict[feature], dict), \
            'Please specify a dict for every feature (empty dict if default)'

        # Check if the process for the given feature has been modified
        if process in input_dict[feature].keys():
            result[feature] = []
            for m in input_dict[feature][process]:
                MethodKeys.key_check(m)
                method_name = m[MethodKeys.METHOD]
                parameters = m[MethodKeys.PARAMETERS]
                # Check if the selected method exists and whether the
                # right parameters are given
                methods.check_name_and_params(method_name, parameters)
                result[feature].append(m)

    return result


class MethodDescriptions:
    MODES = {}

    @classmethod
    def check_name_and_params(cls, method_name, method_params):
        """
        Args:
            method_name:
            method_params:
        """
        assert method_name in cls.MODES.keys(), \
            'Choose one of the defined methods: {}'.format(cls.MODES.keys())

        assert all(
            p in method_params.keys() for p in cls.MODES[method_name][1]), \
            'All the required params {} of the {} needs to be defined' \
                .format(cls.MODES[method_name][1], method_name)

    @classmethod
    def get_method(cls, method_name):
        """
        Args:
            method_name:
        """
        return cls.MODES[method_name][0]


DEFAULT_DICT = {
    'boolean': {
        'filling': [{'method': 'max', 'parameters': {}}],
        'resampling': [{'method': 'threshold',
                        'parameters': {'c_value': 0,
                                       'cond': 'greater',
                                       'set_value': 1,
                                       'threshold': 0}}],
        'transform': [{'method': 'no_transform', 'parameters': {}}]},
    'float': {
        'filling': [{'method': 'max', 'parameters': {}}],
        'resampling': [{'method': 'mean', 'parameters': {}}],
        'transform': [{'method': 'scale_to_z_score', 'parameters': {}}]},
    'integer': {
        'filling': [{'method': 'max', 'parameters': {}}],
        'resampling': [{'method': 'mean', 'parameters': {}}],
        'transform': [{'method': 'scale_to_z_score', 'parameters': {}}]},
    'string': {
        'filling': [{'method': 'custom', 'parameters': {'custom_value': ''}}],
        'resampling': [{'method': 'mode', 'parameters': {}}],
        'transform': [{'method': 'compute_and_apply_vocabulary',
                       'parameters': {}}]
    }}
