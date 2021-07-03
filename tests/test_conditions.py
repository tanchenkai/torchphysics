import torch
import numpy as np
import pytest
from neural_diff_eq.problem import condition as condi
from neural_diff_eq.problem import datacreator as dc
from neural_diff_eq.problem.domain.domain1D import Interval
from neural_diff_eq.problem.domain.domain2D import Rectangle
from neural_diff_eq.problem.variables.variable import Variable

# Helper functions for testing
def model_function(input):
    return input['x']

def condition_function(model, data):
    return model - data['out']


# Test parent class
def test_create_condition():
    cond = condi.Condition(name='test', norm=torch.nn.MSELoss(), weight=2, 
                           track_gradients=True, data_plot_variables=True)
    assert cond.name == 'test'
    assert isinstance(cond.norm, torch.nn.MSELoss)
    assert cond.weight == 2
    assert cond.track_gradients
    assert cond.data_plot_variables
    assert cond.variables is None


def test_none_methode_condition():
    cond = condi.Condition(name='test', norm=torch.nn.MSELoss())
    assert cond.get_data() is None
    assert cond.get_data_plot_variables() is None    

def test_none_methode_datacreator():
    creator = dc.DataCreator(None, 1)
    assert creator.get_data() is None
    assert creator.divide_dataset_for_int() is None 

def test_new_condition_not_registered():
    cond = condi.Condition(name='test', norm=torch.nn.MSELoss())
    assert not cond.is_registered()


def test_serialize_condition():
    cond = condi.Condition(name='test', norm=torch.nn.MSELoss())
    dct = cond.serialize()
    assert dct['name'] == 'test'
    assert dct['norm'] == 'MSELoss'
    assert dct['weight'] == 1


# Test DiffEqCondition
def test_create_diffeqcondition():
    cond = condi.DiffEqCondition(pde=condition_function,
                                 norm=torch.nn.MSELoss())
    assert cond.name == 'pde'
    assert isinstance(cond.norm, torch.nn.MSELoss)
    assert cond.weight == 1
    assert cond.track_gradients
    assert not cond.data_plot_variables
    assert cond.variables is None
    assert cond.datacreator.dataset_size == 10000
    assert cond.pde == condition_function


def test_forward_diffeqcondition_with_MSE():
    data = {'x': torch.FloatTensor([[1, 1], [1, 0]]), 
            'out': torch.FloatTensor([[1, 1], [1, 0]])}
    cond = condi.DiffEqCondition(pde=condition_function,
                                 norm=torch.nn.MSELoss())
    out = cond.forward(model_function, data)
    assert out == 0  
    data = {'x': torch.FloatTensor([[1, 1], [1, 0]]), 
            'out': torch.FloatTensor([[0, 1], [1, 0]])}
    out = cond.forward(model_function, data)
    assert out == 1/4  


def test_forward_diffeqcondition_with_L1Loss():
    data = {'x': torch.FloatTensor([[1, 1], [1, 0]]), 
            'out': torch.FloatTensor([[1, 1], [1, 0]])}
    cond = condi.DiffEqCondition(pde=condition_function,
                                 norm=torch.nn.L1Loss(reduction='sum'))
    out = cond.forward(model_function, data)
    assert out == 0  
    data = {'x': torch.FloatTensor([[1, 1], [1, 0]]), 
            'out': torch.FloatTensor([[0, 1], [1, 0]])}
    out = cond.forward(model_function, data)
    assert out == 1


def test_get_data_diffeqcondition_not_registered():
    cond = condi.DiffEqCondition(pde=condition_function,
                                 norm=torch.nn.MSELoss())
    with pytest.raises(RuntimeError):
        cond.get_data()


def test_get_data_diffeqcondition_wrong_strategy():
    cond = condi.DiffEqCondition(pde=condition_function,
                                 norm=torch.nn.MSELoss(), 
                                 sampling_strategy='test')
    cond.variables = {}
    with pytest.raises(NotImplementedError):
        cond.get_data()


def test_data_sampling_with_int_random_diffeqcondition(): 
    cond = condi.DiffEqCondition(pde=condition_function,
                                 norm=torch.nn.MSELoss(), 
                                 dataset_size=500, 
                                 sampling_strategy='random')
    x = Variable(name='x', domain=Interval(0, 1))
    t = Variable(name='t', domain=Interval(-1, 1))
    cond.variables = {'x': x, 't': t}
    data = cond.get_data()
    assert np.shape(data['x']) == (500, 1)
    assert np.shape(data['t']) == (500, 1)
    assert t.domain.is_inside(data['t']).all()
    assert not x.domain.is_inside(data['t']).all()


def test_data_sampling_with_int_grid_diffeqcondition(): 
    cond = condi.DiffEqCondition(pde=condition_function,
                                 norm=torch.nn.MSELoss(), 
                                 dataset_size=100, 
                                 sampling_strategy='grid')
    x = Variable(name='x', domain=Interval(0, 1))
    t = Variable(name='t', domain=Interval(-1, 1))
    cond.variables = {'x': x, 't': t}
    data = cond.get_data()
    assert np.shape(data['x']) == (100, 1)
    assert np.shape(data['t']) == (100, 1)
    for i in range(9):
        assert data['x'][i] == data['x'][i+1]     
    assert np.equal(data['t'][0:10], data['t'][10:20]).all()


def test_data_sampling_with_int_grid_divide_2D_1D_diffeqcondition(): 
    cond = condi.DiffEqCondition(pde=condition_function,
                                 norm=torch.nn.MSELoss(), 
                                 dataset_size=1000, 
                                 sampling_strategy='grid')
    x = Variable(name='x', domain=Rectangle([0, 0], [1, 0], [0, 1]))
    t = Variable(name='t', domain=Interval(-1, 1))
    cond.variables = {'x': x, 't': t}
    data = cond.get_data()
    assert np.shape(data['x']) == (1000, 2)
    assert np.shape(data['t']) == (1000, 1)
    for i in range(9):
        assert np.equal(data['x'][i], data['x'][i+1]).all()  
        assert np.equal(data['x'][100+i], data['x'][i+101]).all()  
    assert np.equal(data['t'][0:100], data['t'][100:200]).all()


def test_data_sampling_with_wrong_input_diffeqcondition(): 
    cond = condi.DiffEqCondition(pde=condition_function,
                                 norm=torch.nn.MSELoss(), 
                                 dataset_size='42', 
                                 sampling_strategy='grid')
    x = Variable(name='x', domain=Rectangle([0, 0], [1, 0], [0, 1]))
    t = Variable(name='t', domain=Interval(-1, 1))
    cond.variables = {'x': x, 't': t}
    with pytest.raises(TypeError):
        _ = cond.get_data()


def test_data_sampling_with_list_diffeqcondition(): 
    cond = condi.DiffEqCondition(pde=condition_function,
                                 norm=torch.nn.MSELoss(), 
                                 dataset_size=[10, 10, 5], 
                                 sampling_strategy='random')
    x = Variable(name='x', domain=Interval(0, 1))
    t = Variable(name='t', domain=Interval(-1, 1))
    D = Variable(name='D', domain=Interval(2, 3))
    cond.variables = {'x': x, 't': t, 'D': D}
    data = cond.get_data()
    assert np.shape(data['x']) == (500, 1)
    assert np.shape(data['t']) == (500, 1)
    assert np.shape(data['D']) == (500, 1)
    assert t.domain.is_inside(data['t']).all()
    assert x.domain.is_inside(data['x']).all()
    assert D.domain.is_inside(data['D']).all()
    assert not x.domain.is_inside(data['t']).all()
    assert not D.domain.is_inside(data['t']).all()


def test_data_sampling_with_dic_diffeqcondition(): 
    cond = condi.DiffEqCondition(pde=condition_function,
                                 norm=torch.nn.MSELoss(), 
                                 dataset_size={'t': 5, 'x': 10}, 
                                 sampling_strategy='grid')
    x = Variable(name='x', domain=Rectangle([0, 0], [1, 0], [0, 1]))
    t = Variable(name='t', domain=Interval(-1, 1))
    cond.variables = {'x': x, 't': t}
    data = cond.get_data()
    assert np.shape(data['x']) == (50, 2)
    assert np.shape(data['t']) == (50, 1)
    assert t.domain.is_inside(data['t']).all()
    assert x.domain.is_inside(data['x']).all()


def test_serialize_diffeqcondition():
    cond = condi.DiffEqCondition(pde=condition_function,
                                 norm=torch.nn.MSELoss(), 
                                 dataset_size=500, 
                                 sampling_strategy='grid')
    dct = cond.serialize()
    assert dct['sampling_strategy'] == 'grid'
    assert dct['pde'] == 'condition_function'
    assert dct['dataset_size'] == 500


def test_get_data_plot_varibales_diffeqcondition():
    cond = condi.DiffEqCondition(pde=condition_function,
                                 norm=torch.nn.MSELoss(), 
                                 dataset_size=500, 
                                 sampling_strategy='grid')
    x = Variable(name='x', domain=Interval(0, 1))
    t = Variable(name='t', domain=Interval(-1, 1))
    cond.variables = {'x': x, 't': t}
    assert cond.get_data_plot_variables() is None
    cond.data_plot_variables = True
    assert cond.get_data_plot_variables() == {'x': x, 't': t}
    cond.data_plot_variables = x
    assert cond.get_data_plot_variables() == x


# Test datacondition
def create_data_condition():
    return condi.DataCondition(name='test',
                               norm=torch.nn.MSELoss(), 
                               data_x={'x': torch.ones(5)}, 
                               data_u=torch.tensor([1, 2, 1, 1, 0]))
def test_create_datacondition():
    cond = create_data_condition()
    assert cond.name == 'test'
    assert isinstance(cond.norm, torch.nn.MSELoss)
    assert cond.weight == 1
    assert not cond.track_gradients
    assert not cond.data_plot_variables
    assert cond.variables is None
    assert torch.equal(cond.data_x['x'], torch.ones(5))
    assert torch.equal(cond.data_u, torch.tensor([1, 2, 1, 1, 0]))


def test_get_data_plot_varibales_datacondition():
    cond = create_data_condition()
    assert cond.get_data_plot_variables() is None


def test_serialize_datacondition():
    cond = create_data_condition()
    dct = cond.serialize()
    assert dct['name'] == 'test'
    assert dct['norm'] == 'MSELoss'
    assert dct['weight'] == 1


def test_get_data_datacondition_not_registered():
    cond = create_data_condition()
    with pytest.raises(RuntimeError):
        cond.get_data()


def test_get_data_datacondition():
    cond = create_data_condition()
    x = Variable(name='x', domain=Interval(0, 1))
    t = Variable(name='t', domain=Interval(-1, 1))
    cond.variables = {'x': x, 't': t}
    data, target = cond.get_data()
    assert torch.equal(data['x'], torch.ones(5))
    assert torch.equal(target, torch.tensor([1, 2, 1, 1, 0]))


def test_forward_dataqcondition():
    cond = create_data_condition()
    cond.variables = {'x': 1}
    data = cond.get_data()
    out = cond.forward(model_function, data)
    assert out == 2/5  


# Test boundary conditions
def test_parent_boundary_condition():
    cond = condi.BoundaryCondition(name='test', 
                                   norm=torch.nn.MSELoss(),
                                   track_gradients=True)
    assert cond.boundary_variable is None


def test_serialize_boundary_condition():
    cond = condi.BoundaryCondition(name='test', 
                                   norm=torch.nn.MSELoss(),
                                   track_gradients=True)
    dct = cond.serialize()
    assert dct['boundary_variable'] is None


def test_get_data_plot_varibales_boundary_conditon():
    cond = condi.BoundaryCondition(name='test', 
                                   norm=torch.nn.MSELoss(),
                                   track_gradients=True)
    x = Variable(name='x', domain=Interval(0, 1))
    t = Variable(name='t', domain=Interval(-1, 1))
    cond.variables = {'x': x}
    cond.boundary_variable = t
    cond.data_plot_variables = False
    assert cond.get_data_plot_variables() is None
    cond.data_plot_variables = True
    assert cond.get_data_plot_variables() == t
    cond.data_plot_variables = x
    assert cond.get_data_plot_variables() == x


# Test dirichlet condition
def dirichlet_fun(input):
    return input['x']

def create_dirichlet():
    return condi.DirichletCondition(dirichlet_fun=dirichlet_fun,
                                    name='test diri',
                                    norm=torch.nn.MSELoss(),
                                    sampling_strategy='grid',
                                    boundary_sampling_strategy='random',
                                    weight=1.5,
                                    dataset_size=50,
                                    data_plot_variables=True)


def test_create_dirichlet_condition():
    cond = create_dirichlet()
    assert cond.dirichlet_fun == dirichlet_fun
    assert cond.name == 'test diri'
    assert isinstance(cond.norm, torch.nn.MSELoss)
    assert cond.datacreator.sampling_strategy == 'grid'
    assert cond.datacreator.boundary_sampling_strategy == 'random'
    assert cond.boundary_variable is None
    assert cond.weight == 1.5
    assert cond.datacreator.dataset_size == 50
    assert cond.data_plot_variables 


def test_serialize_dirichlet_condition():
    cond = create_dirichlet()
    dct = cond.serialize()
    assert dct['dirichlet_fun'] == 'dirichlet_fun'
    assert dct['dataset_size'] == 50
    assert dct['sampling_strategy'] == 'grid'
    assert dct['boundary_sampling_strategy'] == 'random'


def test_get_data_dirichlet_qcondition_not_registered():
    cond = create_dirichlet()
    with pytest.raises(RuntimeError):
        cond.get_data()


def test_get_data_dirichlet_condition():
    cond = create_dirichlet()
    x = Variable(name='x', domain=Interval(0, 1))
    t = Variable(name='t', domain=Interval(-3, -2))
    cond.variables = {'x': x, 't': t}
    cond.boundary_variable = 't'
    data, target = cond.get_data()
    assert np.shape(data['x']) == (64, 1)
    assert np.shape(data['t']) == (64, 1)
    assert t.domain.is_inside(data['t']).all()
    assert not x.domain.is_inside(data['t']).all()
    assert np.equal(data['x'], target).all()


def test_forward_dirichlet_condition():
    cond = create_dirichlet()
    data = ({'x': torch.ones((2,1))}, torch.zeros((2,1)))
    out = cond.forward(model_function, data)
    assert out.item() == 1 
    assert isinstance(out, torch.Tensor)


def test_boundary_data_meshing():
    input_dic = {'x': np.array([[1], [2]]), 't': np.array([[1, 1], [3, 0]])}
    data_points = np.array([[0], [1]])
    creator = dc.BoundaryDataCreator(variables= {'x': 1, 't': 1, 'r':1}, 
                                     dataset_size=10, 
                                     sampling_strategy='random',
                                     boundary_sampling_strategy='random')  
    creator.boundary_variable = 'r'
    mesh_data = creator.mesh_inner_and_boundary_data(input_dic, data_points)
    solution = np.array([[1, 1, 1, 0], [2, 3, 0, 0], [1, 1, 1, 1], [2, 3, 0, 1]])
    assert np.equal(mesh_data['x'], solution[:, :1]).all()
    assert np.equal(mesh_data['t'], solution[:, 1:3]).all()
    assert np.equal(mesh_data['r'], solution[:, 3:]).all()


def test_boundary_data_creation_random_random_int():
    x = Variable(name='x', domain=Interval(0, 1))
    t = Variable(name='t', domain=Interval(-3, -2))
    creator = dc.BoundaryDataCreator(variables= {'x': x, 't': t}, 
                                     dataset_size=10, 
                                     sampling_strategy='random',
                                     boundary_sampling_strategy='random')
    creator.boundary_variable = 't'
    data = creator.get_data()
    assert np.shape(data['x']) == (10, 1)
    assert np.shape(data['t']) == (10, 1)
    assert x.domain.is_inside(data['x']).all()
    assert t.domain.is_inside(data['t']).all()
    assert not x.domain.is_inside(data['t']).all()


def test_boundary_data_creation_grid_random_int():
    x = Variable(name='x', domain=Interval(0, 1))
    t = Variable(name='t', domain=Interval(-3, -2))
    creator = dc.BoundaryDataCreator(variables= {'x': x, 't': t}, 
                                     dataset_size=25, 
                                     sampling_strategy='grid',
                                     boundary_sampling_strategy='random')
    creator.boundary_variable = 't'
    data = creator.get_data()
    assert np.shape(data['x']) == (25, 1)
    assert np.shape(data['t']) == (25, 1)
    assert x.domain.is_inside(data['x']).all()
    assert t.domain.is_inside(data['t']).all()
    for i in range(len(data['t'])):
        assert data['t'][i] == -3 or data['t'][i] == -2
    assert not x.domain.is_inside(data['t']).all()


def test_boundary_data_creation_random_grid_int():
    x = Variable(name='x', domain=Interval(0, 1))
    t = Variable(name='t', domain=Interval(-1, -0.1))
    creator = dc.BoundaryDataCreator(variables= {'x': x, 't': t}, 
                                     dataset_size=25, 
                                     sampling_strategy='random',
                                     boundary_sampling_strategy='grid')
    creator.boundary_variable = 't'
    data = creator.get_data()
    assert np.shape(data['x']) == (25, 1)
    assert np.shape(data['t']) == (25, 1)
    assert x.domain.is_inside(data['x']).all()
    assert t.domain.is_inside(data['t']).all()
    for i in range(len(data['t'])):
        assert data['t'][i] == -1 or data['t'][i] == -0.1
    assert not x.domain.is_inside(data['t']).all()


def test_boundary_data_creation_grid_grid_int():
    x = Variable(name='x', domain=Interval(0, 1))
    t = Variable(name='t', domain=Interval(-1, -0.1))
    creator = dc.BoundaryDataCreator(variables= {'x': x, 't': t}, 
                                     dataset_size=30, 
                                     sampling_strategy='grid',
                                     boundary_sampling_strategy='grid')
    creator.boundary_variable = 't'
    data = creator.get_data()
    assert np.shape(data['x']) == (30, 1)
    assert np.shape(data['t']) == (30, 1)
    assert x.domain.is_inside(data['x']).all()
    assert t.domain.is_inside(data['t']).all()
    for i in range(len(data['t'])):
        assert data['t'][i] == -1 or data['t'][i] == -0.1
    assert not x.domain.is_inside(data['t']).all()


def test_boundary_data_creation_random_lower_bound_int():
    x = Variable(name='x', domain=Interval(0, 1))
    t = Variable(name='t', domain=Interval(-1, -0.1))
    creator = dc.BoundaryDataCreator(variables= {'x': x, 't': t}, 
                                     dataset_size=30, 
                                     sampling_strategy='random',
                                     boundary_sampling_strategy='lower_bound_only')
    creator.boundary_variable = 't'
    data = creator.get_data()
    assert np.shape(data['x']) == (30, 1)
    assert np.shape(data['t']) == (30, 1)
    assert x.domain.is_inside(data['x']).all()
    assert t.domain.is_inside(data['t']).all()
    for i in range(len(data['t'])):
        assert data['t'][i] == -1 
    assert not x.domain.is_inside(data['t']).all()


def test_boundary_data_creation_grid_lower_upper_bound_int():
    x = Variable(name='x', domain=Interval(0, 1))
    t = Variable(name='t', domain=Interval(-1, -0.1))
    creator = dc.BoundaryDataCreator(variables= {'x': x, 't': t}, 
                                     dataset_size=30, 
                                     sampling_strategy='grid',
                                     boundary_sampling_strategy='lower_bound_only')
    creator.boundary_variable = 't'
    data = creator.get_data()
    assert np.shape(data['x']) == (30, 1)
    assert np.shape(data['t']) == (30, 1)
    assert x.domain.is_inside(data['x']).all()
    assert t.domain.is_inside(data['t']).all()
    for i in range(len(data['t'])):
        assert data['t'][i] == -1 
    assert not x.domain.is_inside(data['t']).all()
    creator.boundary_sampling_strategy = 'upper_bound_only'
    data = creator.get_data()
    assert np.shape(data['x']) == (30, 1)
    assert np.shape(data['t']) == (30, 1)
    assert x.domain.is_inside(data['x']).all()
    assert t.domain.is_inside(data['t']).all()
    for i in range(len(data['t'])):
        assert data['t'][i] == -0.1
    assert not x.domain.is_inside(data['t']).all()

def test_boundary_data_creation_with_list():
    x = Variable(name='x', domain=Interval(0, 1))
    t = Variable(name='t', domain=Interval(-1, -0.1))
    creator = dc.BoundaryDataCreator(variables= {'x': x, 't': t}, 
                                     dataset_size=[30, 2], 
                                     sampling_strategy='grid',
                                     boundary_sampling_strategy='grid')
    creator.boundary_variable = 't'
    data = creator.get_data()
    assert np.shape(data['x']) == (60, 1)
    assert np.shape(data['t']) == (60, 1)
    assert x.domain.is_inside(data['x']).all()
    assert t.domain.is_inside(data['t']).all()
    for i in range(len(data['t'])):
        assert data['t'][i] == -1 or data['t'][i] == -0.1
    assert not x.domain.is_inside(data['t']).all()


def test_boundary_data_creation_with_dic():
    x = Variable(name='x', domain=Interval(0, 1))
    t = Variable(name='t', domain=Interval(-1, -0.1))
    creator = dc.BoundaryDataCreator(variables= {'x': x, 't': t}, 
                                     dataset_size={'x':10, 't':1}, 
                                     sampling_strategy='grid',
                                     boundary_sampling_strategy='lower_bound_only')
    creator.boundary_variable = 't'
    data = creator.get_data()
    assert np.shape(data['x']) == (10, 1)
    assert np.shape(data['t']) == (10, 1)
    assert x.domain.is_inside(data['x']).all()
    assert t.domain.is_inside(data['t']).all()
    for i in range(len(data['t'])):
        assert data['t'][i] == -1
    assert not x.domain.is_inside(data['t']).all()


def test_boundary_data_creation_with_3_inputs():
    x = Variable(name='x', domain=Interval(0, 1))
    t = Variable(name='t', domain=Interval(-1, -0.1))
    D = Variable(name='D', domain=Interval(3, 4))
    creator = dc.BoundaryDataCreator(variables= {'x': x, 't': t, 'D': D}, 
                                     dataset_size=[10, 1, 10], 
                                     sampling_strategy='grid',
                                     boundary_sampling_strategy='lower_bound_only')
    creator.boundary_variable = 'x'
    data = creator.get_data()
    assert np.shape(data['x']) == (100, 1)
    assert np.shape(data['D']) == (100, 1)
    assert np.shape(data['t']) == (100, 1)
    assert x.domain.is_inside(data['x']).all()
    assert D.domain.is_inside(data['D']).all()
    assert t.domain.is_inside(data['t']).all()
    for i in range(len(data['x'])):
        assert data['x'][i] == 0
    assert not x.domain.is_inside(data['t']).all()
    assert not x.domain.is_inside(data['D']).all()


def test_boundary_data_creation_with_2D_boundary_grid_grid():
    x = Variable(name='x', domain=Rectangle([0, 0], [1, 0], [0, 1]))
    t = Variable(name='t', domain=Interval(-1, -0.1))
    D = Variable(name='D', domain=Interval(3, 4))
    creator = dc.BoundaryDataCreator(variables= {'x': x, 't': t, 'D': D}, 
                                     dataset_size=[10, 10, 10], 
                                     sampling_strategy='grid',
                                     boundary_sampling_strategy='grid')
    creator.boundary_variable = 'x'
    data = creator.get_data()
    assert np.shape(data['x']) == (1000, 2)
    assert np.shape(data['D']) == (1000, 1)
    assert np.shape(data['t']) == (1000, 1)
    assert x.domain.is_on_boundary(data['x']).all()
    assert D.domain.is_inside(data['D']).all()
    assert t.domain.is_inside(data['t']).all()
    assert not D.domain.is_inside(data['t']).all()


def test_boundary_data_creation_with_2D_boundary_grid_grid_int():
    x = Variable(name='x', domain=Rectangle([0, 0], [1, 0], [0, 1]))
    t = Variable(name='t', domain=Interval(-1, -0.1))
    creator = dc.BoundaryDataCreator(variables= {'x': x, 't': t}, 
                                     dataset_size=1000, 
                                     sampling_strategy='grid',
                                     boundary_sampling_strategy='grid')
    creator.boundary_variable = 'x'
    data = creator.get_data()
    assert np.shape(data['x']) == (1000, 2)
    assert np.shape(data['t']) == (1000, 1)
    assert x.domain.is_on_boundary(data['x']).all()
    assert t.domain.is_inside(data['t']).all()
    assert np.equal(data['t'][0:10], data['t'][10:20]).all()
    for i in range(9):
        assert np.equal(data['x'][i], data['x'][i+1]).all()


def test_boundary_data_creation_with_2D_boundary_random_grid_int():
    x = Variable(name='x', domain=Rectangle([0, 0], [1, 0], [0, 1]))
    t = Variable(name='t', domain=Interval(-1, -0.1))
    creator = dc.BoundaryDataCreator(variables= {'x': x, 't': t}, 
                                     dataset_size=100, 
                                     sampling_strategy='random',
                                     boundary_sampling_strategy='grid')
    creator.boundary_variable = 'x'
    data = creator.get_data()
    assert np.shape(data['x']) == (100, 2)
    assert np.shape(data['t']) == (100, 1)
    assert x.domain.is_on_boundary(data['x']).all()
    assert t.domain.is_inside(data['t']).all()


def test_boundary_data_creation_with_2D_boundary_grid_random_int():
    x = Variable(name='x', domain=Rectangle([0, 0], [1, 0], [0, 1]))
    t = Variable(name='t', domain=Interval(-1, -0.1))
    creator = dc.BoundaryDataCreator(variables= {'x': x, 't': t}, 
                                     dataset_size=100, 
                                     sampling_strategy='grid',
                                     boundary_sampling_strategy='random')
    creator.boundary_variable = 'x'
    data = creator.get_data()
    assert np.shape(data['x']) == (100, 2)
    assert np.shape(data['t']) == (100, 1)
    assert x.domain.is_on_boundary(data['x']).all()
    assert t.domain.is_inside(data['t']).all()


# Test neumann conditions
def neumann_fun(input):
    return np.zeros_like(input['t'])

def create_neumann():
    return condi.NeumannCondition(neumann_fun=neumann_fun,
                                  name='test neumann',
                                  norm=torch.nn.MSELoss(),
                                  sampling_strategy='grid',
                                  boundary_sampling_strategy='grid',
                                  weight=1,
                                  dataset_size=50,
                                  data_plot_variables=True)


def test_create_neumann_condition():
    cond = create_neumann()
    assert cond.neumann_fun == neumann_fun
    assert cond.name == 'test neumann'
    assert isinstance(cond.norm, torch.nn.MSELoss)
    assert cond.datacreator.sampling_strategy == 'grid'
    assert cond.datacreator.boundary_sampling_strategy == 'grid'
    assert cond.boundary_variable is None
    assert cond.weight == 1
    assert cond.datacreator.dataset_size == 50
    assert cond.data_plot_variables 


def test_serialize_neumann_condition():
    cond = create_neumann()
    dct = cond.serialize()
    assert dct['neumann_fun'] == 'neumann_fun'
    assert dct['dataset_size'] == 50
    assert dct['sampling_strategy'] == 'grid'
    assert dct['boundary_sampling_strategy'] == 'grid'


def test_get_data_neumann_condition_not_registered():
    cond = create_neumann()
    with pytest.raises(RuntimeError):
        cond.get_data()


def test_get_data_neumann_condition():
    cond = create_neumann()
    x = Variable(name='x', domain=Rectangle([0, 0], [1, 0], [0, 1]))
    t = Variable(name='t', domain=Interval(-3, -2))
    cond.variables = {'x': x, 't': t}
    cond.boundary_variable = 'x'
    data, target, normals = cond.get_data()
    assert np.shape(data['x']) == (64, 2)
    assert np.shape(data['t']) == (64, 1)
    assert np.shape(normals) == (64, 2)
    assert np.shape(target) == (64, 1)
    assert t.domain.is_inside(data['t']).all()
    assert x.domain.is_on_boundary(data['x']).all()
    for i in range(len(normals)):
        assert np.isclose(np.linalg.norm(normals[i]), 1)
        assert np.isclose(target[i], 0)
    for i in range(len(normals)):
        new_normal = x.domain.boundary_normal([data['x'][i]])
        assert np.allclose(new_normal, normals[i])


def test_forward_neumann_condition():
    cond = create_neumann()
    x = Variable(name='x', domain=Rectangle([0, 0], [1, 0], [0, 1]))
    t = Variable(name='t', domain=Interval(-3, -2))
    cond.variables = {'x': x, 't': t}
    cond.boundary_variable = 'x'
    data, target, normals = cond.get_data()
    target = torch.from_numpy(target)
    normals = torch.from_numpy(normals)
    data['x'] = torch.from_numpy(data['x'])
    data['x'].requires_grad = True 
    data = data, target, normals
    out = cond.forward(model_function, data)
    assert out.item() == 1 
    assert isinstance(out, torch.Tensor)
    norm = torch.nn.MSELoss()
    assert torch.isclose(out, norm(normals.sum(dim=1, keepdim=True), target))