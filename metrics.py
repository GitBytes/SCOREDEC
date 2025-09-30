import numpy as np
import pandas as pd
import re
from sympy import sympify, symbols, Array, Matrix
from sympy import lambdify

class Metrics:

    def __init__(
            self,
            expr="x",
            custom_function=None,
            input_dict=None
    ):

        self.expr = expr
        self.custom_function = custom_function
        self.input_dict = input_dict

        self._gen_function_from_str()


    def _gen_function(self):
        """
        Method to generate python based
        """
        if self.custom_function is None:
            assert self.expr is not None

        return None


    def _gen_function_from_str(self):
        """
        Method to generate
        """
        #First get all the symbols
        #Only [a-zA-z]+ is allowed
        #
        _regex = r"([a-zA-Z]+)"
        _syms = re.findall(_regex, self.expr)
        syms = list(set(_syms))

        #set up symbols
        syms_dict = dict()
        for key in syms:
            syms_dict[key] = symbols(key)

        #Check that all the col headers match up with the individual values
        self._check_col_headers(syms)
        #Evaluate the function
        sympy_dict = self._convert_input_to_sympy() #cpmvert np arrays to sympy arrays
        print(f"sympy dict: {sympy_dict}")
        _expr = sympify(self.expr)
        f = lambdify(syms, _expr, 'numpy') #vectorize the function
        output = f(**sympy_dict)
        return None


    def _check_col_headers(self, list_of_symbols):
        """
        Method to check the keys to the column headers
        """
        assert type(self.input_dict) == dict
        assert set(list_of_symbols) <= set(self.input_dict.keys())
        return None

    def _convert_input_to_sympy(self):
        """
        Method to convert input array to Sympy Arrays or Matriccs
        """
        sympy_dict = self.input_dict.copy()
        for key, val in self.input_dict.items():
            if len(val.shape) <= 1:
                sympy_dict[key] = Array(val)
            else:
                sympy_dict[key] = Matrix(val)
        return sympy_dict

# class OutputVars:
#
#     def __init__(self):


if __name__ == "__main__":
    col_headers = {
        "x": np.zeros((10, )),
        "y": np.zeros((10, ))
    }
    TestMetrics = Metrics(expr="x**2 + 2*y", input_dict=col_headers)
