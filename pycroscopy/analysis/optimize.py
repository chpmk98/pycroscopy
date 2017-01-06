"""
Created on 12/15/16 10:08 AM
@author: Numan Laanait
"""

from warnings import warn
import numpy as np
import sys
import multiprocessing as mp
from .guess_methods import GuessMethods
from .fit_methods import Fit_Methods
import scipy

def targetFuncGuess(args, **kwargs):
    """
    Needed to create mappable function for multiprocessing
    :param args:
    :param kwargs:
    :return:
    """
    func = Optimize._guessFunc(args[-1])
    results = func(args[0])
    return results

def targetFuncFit(args, **kwargs):
    """
    Needed to create mappable function for multiprocessing
    :param args:
    :param kwargs:
    :return:
    """
    solver, solver_options,func = Optimize._initiateSolverAndObjFunc(args[-1])
    results = solver(func, args[1], args=[args[0]])
    return results

class Optimize(object):
    """
    In charge of all optimization and computation and is used within the Model Class.
    """

    def __init__(self, data=np.array([]), guess=np.array([]), parallel=True):
        """

        :param data:
        """
        if isinstance(data, np.ndarray):
            self.data = data
        if isinstance(guess, np.ndarray):
            self.guess = guess
        else:
            warn('Error: data and guess must be numpy.ndarray. Exiting...')
            sys.exit()
        self._parallel = parallel


    def _guessFunc(self):
        gm = GuessMethods()
        if self.strategy in gm.methods:
            func = gm.__getattribute__(self.strategy)(**self.options)
            return func
        else:
            warn('Error: %s is not implemented in pycroscopy.analysis.GuessMethods to find guesses' % self.strategy)



    def computeGuess(self, processors = 1, strategy='wavelet_peaks',
                     options={"peak_widths": np.array([10,200]),"peak_step":20}, **kwargs):
        """

        Parameters
        ----------
        data
        strategy: string
            Default is 'Wavelet_Peaks'.
            Can be one of ['wavelet_peaks', 'relative_maximum', 'gaussian_processes']. For updated list, run GuessMethods.methods
        options: dict
            Default: Options for wavelet_peaks{"peaks_widths": np.array([10,200]), "peak_step":20}.
            Dictionary of options passed to strategy. For more info see GuessMethods documentation.

        kwargs:
            processors: int
                number of processors to use. Default all processors on the system except for 1.

        Returns
        -------

        """
        self.strategy = strategy
        self.options = options
        processors = processors
        gm = GuessMethods()
        if strategy in gm.methods:
            # func = gm.__getattribute__(strategy)(**options)
            results = list()
            if self._parallel:
                # start pool of workers
                print('Computing Jobs In parallel ... launching %i kernels...' % processors)
                pool = mp.Pool(processors)
                # Vectorize tasks
                tasks = [(vector, self) for vector in self.data]
                chunk = int(self.data.shape[0] / processors)
                # Map them across processors
                jobs = pool.imap(targetFuncGuess, tasks, chunksize=chunk)
                # get Results from different processes
                results = [j for j in jobs]
                print('Extracted Results...')
                # Finished reading the entire data set
                print('closing %i kernels...' % processors)
                pool.close()
                return results

            else:
                print("Computing Guesses In Serial ...")
                results = [targetFuncGuess((vector, self)) for vector in self.data]
                return results
        else:
            warn('Error: %s is not implemented in pycroscopy.analysis.GuessMethods to find guesses' % strategy)

    def _initiateSolverAndObjFunc(self):
        if self.solver_type in scipy.optimize.__dict__.keys():
            solver = scipy.optimize.__dict__[self.solver_type]
        if self.obj_func is None:
            fm = Fit_Methods()
            func = fm.__getattribute__(self.obj_func_name)(self.obj_func_xvals)
        return solver,self.solver_options, func

            # if self.obj_func_class is 'Fit_Methods':
            #     fm = fit_methods.


    # def _fitFunc(self):
    #
    #
    #     def _callSolver(input):
    #         data = input[0]
    #         guess = input[1]
    #         results = self.solver.__call__(func, guess, args=[data], **kwargs)
    #         self.solver.__call__(func, guess, args=[data], **kwargs)
    #         return results

    def computeFit(self, processors = 1, solver_type='least_squares', solver_options={},
                   obj_func={'class':'Fit_Methods','obj_func':'SHO','xvals':np.array([])}):
        """

        Parameters
        ----------
        data
        solver_type : string
            Optimization solver to use (minimize,least_sq, etc...). For additional info see scipy.optimize
        solver_options: dict()
            Default: dict()
            Dictionary of options passed to solver. For additional info see scipy.optimize
        obj_func: dict()
            Default is 'SHO'.
            Can be one of ['wavelet_peaks', 'relative_maximum', 'gaussian_processes']. For updated list, run GuessMethods.methods

        Returns
        -------

        """
        self.solver_type = solver_type
        self.solver_options = solver_options
        if self.solver_type not in scipy.optimize.__dict__.keys():
            warn('Solver %s does not exist!. For additional info see scipy.optimize' % (solver_type))
            sys.exit()
        if obj_func['class'] is None:
            self.obj_func = obj_func['obj_func']
        else:
            self.obj_func_xvals = obj_func['xvals']
            self.obj_func = None
            self.obj_func_name = obj_func['obj_func']
            self.obj_func_class = obj_func['class']

        # def _callSolver(input):
        #     data = input[0]
        #     guess = input[1]
        #     results = self.solver.__call__(func, guess, args=[data], **kwargs)
        #     self.solver.__call__(func, guess, args=[data], **kwargs)
        #     return results

        if self._parallel:
            # start pool of workers
            print('Computing Jobs In parallel ... launching %i kernels...' % processors)
            pool = mp.Pool(processors)
            # Vectorize tasks
            tasks = [(vector, guess, self) for vector, guess in zip(self.data, self.guess)]
            chunk = int(self.data.shape[0] / processors)
            # Map them across processors
            jobs = pool.imap(targetFuncFit, tasks, chunksize=chunk)
            # get Results from different processes
            results = [j for j in jobs]
            # Finished reading the entire data set
            print('closing %i kernels...' % processors)
            pool.close()
            return results

        else:
            print("Computing Fits In Serial ...")
            solver, solver_options, func = self._initiateSolverAndObjFunc()
            results = [solver(func, guess, args=[vector]) for vector, guess in zip(self.data, self.guess)]
            return results