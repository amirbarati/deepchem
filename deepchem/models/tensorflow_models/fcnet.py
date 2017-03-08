"""TensorFlow implementation of fully connected networks. 
"""
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import time
import numpy as np
import tensorflow as tf

import deepchem as dc
from deepchem.nn import model_ops
from deepchem.utils.save import log
from deepchem.models.tensorflow_models import TensorflowGraph
from deepchem.models.tensorflow_models import TensorflowGraphModel
from deepchem.models.tensorflow_models import TensorflowClassifier
from deepchem.models.tensorflow_models import TensorflowRegressor
from deepchem.metrics import to_one_hot


class TensorflowMultiTaskClassifier(TensorflowClassifier):
  """Implements an icml model as configured in a model_config.proto."""

  def build(self, graph, name_scopes, training):
    """Constructs the graph architecture as specified in its config.

    This method creates the following Placeholders:
      mol_features: Molecule descriptor (e.g. fingerprint) tensor with shape
        batch_size x n_features.
    """
    placeholder_scope = TensorflowGraph.get_placeholder_scope(graph,
                                                              name_scopes)
    n_features = self.n_features
    with graph.as_default():
      with placeholder_scope:
        self.mol_features = tf.placeholder(
            tf.float32, shape=[None, n_features], name='mol_features')

      layer_sizes = self.layer_sizes
      weight_init_stddevs = self.weight_init_stddevs
      bias_init_consts = self.bias_init_consts
      dropouts = self.dropouts
      lengths_set = {
          len(layer_sizes),
          len(weight_init_stddevs),
          len(bias_init_consts),
          len(dropouts),
      }
      assert len(lengths_set) == 1, 'All layer params must have same length.'
      n_layers = lengths_set.pop()
      assert n_layers > 0, 'Must have some layers defined.'

      prev_layer = self.mol_features
      prev_layer_size = n_features
      for i in range(n_layers):
        layer = tf.nn.relu(
            model_ops.fully_connected_layer(
                tensor=prev_layer,
                size=layer_sizes[i],
                weight_init=tf.truncated_normal(
                    shape=[prev_layer_size, layer_sizes[i]],
                    stddev=weight_init_stddevs[i]),
                bias_init=tf.constant(
                    value=bias_init_consts[i], shape=[layer_sizes[i]])))
        layer = model_ops.dropout(layer, dropouts[i], training)
        prev_layer = layer
        prev_layer_size = layer_sizes[i]

      output = model_ops.multitask_logits(layer, self.n_tasks)
    return output

  def construct_feed_dict(self, X_b, y_b=None, w_b=None, ids_b=None):
    """Construct a feed dictionary from minibatch data.

    TODO(rbharath): ids_b is not used here. Can we remove it?

    Args:
      X_b: np.ndarray of shape (batch_size, n_features)
      y_b: np.ndarray of shape (batch_size, n_tasks)
      w_b: np.ndarray of shape (batch_size, n_tasks)
      ids_b: List of length (batch_size) with datapoint identifiers.
    """
    orig_dict = {}
    orig_dict["mol_features"] = X_b
    for task in range(self.n_tasks):
      if y_b is not None:
        orig_dict["labels_%d" % task] = to_one_hot(y_b[:, task])
      else:
        # Dummy placeholders
        orig_dict["labels_%d" %
                  task] = np.squeeze(to_one_hot(np.zeros((self.batch_size,))))
      if w_b is not None:
        orig_dict["weights_%d" % task] = w_b[:, task]
      else:
        # Dummy placeholders
        orig_dict["weights_%d" % task] = np.ones((self.batch_size,))
    return TensorflowGraph.get_feed_dict(orig_dict)


class TensorflowMultiTaskRegressor(TensorflowRegressor):
  """Implements an icml model as configured in a model_config.proto."""

  def build(self, graph, name_scopes, training):
    """Constructs the graph architecture as specified in its config.

    This method creates the following Placeholders:
      mol_features: Molecule descriptor (e.g. fingerprint) tensor with shape
        batch_size x n_features.
    """
    n_features = self.n_features
    placeholder_scope = TensorflowGraph.get_placeholder_scope(graph,
                                                              name_scopes)
    with graph.as_default():
      with placeholder_scope:
        self.mol_features = tf.placeholder(
            tf.float32, shape=[None, n_features], name='mol_features')

      layer_sizes = self.layer_sizes
      weight_init_stddevs = self.weight_init_stddevs
      bias_init_consts = self.bias_init_consts
      dropouts = self.dropouts
      lengths_set = {
          len(layer_sizes),
          len(weight_init_stddevs),
          len(bias_init_consts),
          len(dropouts),
      }
      assert len(lengths_set) == 1, 'All layer params must have same length.'
      n_layers = lengths_set.pop()
      assert n_layers > 0, 'Must have some layers defined.'

      prev_layer = self.mol_features
      prev_layer_size = n_features
      for i in range(n_layers):
        layer = tf.nn.relu(
            model_ops.fully_connected_layer(
                tensor=prev_layer,
                size=layer_sizes[i],
                weight_init=tf.truncated_normal(
                    shape=[prev_layer_size, layer_sizes[i]],
                    stddev=weight_init_stddevs[i]),
                bias_init=tf.constant(
                    value=bias_init_consts[i], shape=[layer_sizes[i]])))
        layer = model_ops.dropout(layer, dropouts[i], training)
        prev_layer = layer
        prev_layer_size = layer_sizes[i]

      output = []
      for task in range(self.n_tasks):
        output.append(
            tf.squeeze(
                model_ops.fully_connected_layer(
                    tensor=prev_layer,
                    size=layer_sizes[i],
                    weight_init=tf.truncated_normal(
                        shape=[prev_layer_size, 1],
                        stddev=weight_init_stddevs[i]),
                    bias_init=tf.constant(value=bias_init_consts[i], shape=[1
                                                                           ]))))
      return output

  def construct_feed_dict(self, X_b, y_b=None, w_b=None, ids_b=None):
    """Construct a feed dictionary from minibatch data.

    TODO(rbharath): ids_b is not used here. Can we remove it?

    Args:
      X_b: np.ndarray of shape (batch_size, n_features)
      y_b: np.ndarray of shape (batch_size, n_tasks)
      w_b: np.ndarray of shape (batch_size, n_tasks)
      ids_b: List of length (batch_size) with datapoint identifiers.
    """
    orig_dict = {}
    orig_dict["mol_features"] = X_b
    for task in range(self.n_tasks):
      if y_b is not None:
        orig_dict["labels_%d" % task] = y_b[:, task]
      else:
        # Dummy placeholders
        orig_dict["labels_%d" % task] = np.squeeze(np.zeros((self.batch_size,)))
      if w_b is not None:
        orig_dict["weights_%d" % task] = w_b[:, task]
      else:
        # Dummy placeholders
        orig_dict["weights_%d" % task] = np.ones((self.batch_size,))
    return TensorflowGraph.get_feed_dict(orig_dict)

class TensorflowAdversarialMultiTaskClassifier(TensorflowMultiTaskClassifier):
  """ Adversarial training multitask classifier """

  def get_placeholders(self, graph, name_scopes):
    """Initializes placeholders"""
    placeholder_root = "placeholders"
    placeholder_scope = TensorflowGraph.shared_name_scope(placeholder_root, 
                          graph, name_scopes)
    n_features = self.n_features
    with graph.as_default():
      with placeholder_scope:
        mol_features = tf.placeholder(tf.float32, shape=[None, n_features], 
                      name='mol_features')
    return mol_features

  def construct_graph(self, training, seed):
    """Returns a TensorflowGraph object."""
    graph = tf.Graph() 

    # Lazily created by _get_shared_session().
    shared_session = None

    # Cache of TensorFlow scopes, to prevent '_1' appended scope names
    # when subclass-overridden methods use the same scopes.
    name_scopes = {}
    eps = 0.1

    # Setup graph
    with graph.as_default():
      if seed is not None:
        tf.set_random_seed(seed)
      x = self.get_placeholders(graph, name_scopes)
      output = self.model(graph, x, name_scopes, training)
      labels = self.add_label_placeholders(graph, name_scopes)
      weights = self.add_example_weight_placeholders(graph, name_scopes)

      if training:

        print("Constructing adversarial training graph")
        loss_1 = self.add_training_cost(graph, name_scopes, output, labels, weights)
        print("Calculated loss on true examples")
        grad, = tf.gradients(loss_1, x)
        signed_grad = tf.sign(grad)
        scaled_signed_grad = eps * signed_grad
        adv_x = tf.stop_gradient(x + scaled_signed_grad)
        adv_output = self.model(graph, adv_x, name_scopes, training)
        print("Calculated adversarial output")
        loss_2 = self.add_training_cost(graph, name_scopes, adv_output, labels, weights)
        print("Calculated loss on adversarial examples")
        loss = (loss_1 + loss_2)/2.

    if not training:
      loss = None
      output = self.add_output_ops(graph, output)  # add softmax heads
    return TensorflowGraph(graph=graph,
                           session=shared_session,
                           name_scopes=name_scopes,
                           output=output,
                           labels=labels,
                           weights=weights,
                           loss=loss)
  
  def model(self, graph, x, name_scopes, training):
    """Constructs the graph architecture as specified in its config.

    This method creates the following Placeholders:
      mol_features: Molecule descriptor (e.g. fingerprint) tensor with shape
        batch_size x n_features.
    """
    n_features = self.n_features
    with graph.as_default():

      layer_sizes = self.layer_sizes
      weight_init_stddevs = self.weight_init_stddevs
      bias_init_consts = self.bias_init_consts
      dropouts = self.dropouts
      lengths_set = {
          len(layer_sizes),
          len(weight_init_stddevs),
          len(bias_init_consts),
          len(dropouts),
      }
      assert len(lengths_set) == 1, 'All layer params must have same length.'
      n_layers = lengths_set.pop()
      assert n_layers > 0, 'Must have some layers defined.'

      prev_layer = x
      prev_layer_size = n_features
      for i in range(n_layers):
        layer = tf.nn.relu(
            model_ops.fully_connected_layer(
                tensor=prev_layer,
                size=layer_sizes[i],
                weight_init=tf.truncated_normal(
                    shape=[prev_layer_size, layer_sizes[i]],
                    stddev=weight_init_stddevs[i]),
                bias_init=tf.constant(
                    value=bias_init_consts[i], shape=[layer_sizes[i]])))
        layer = model_ops.dropout(layer, dropouts[i], training)
        prev_layer = layer
        prev_layer_size = layer_sizes[i]

      output = model_ops.multitask_logits(layer, self.n_tasks)
    return output
 
  def fit(self, dataset, nb_epoch=10, max_checkpoints_to_keep=5, 
	  log_every_N_batches=50, **kwargs):
    """Fit the model.

    Parameters
    ---------- 
    dataset: dc.data.Dataset
      Dataset object holding training data 
    nb_epoch: 10
      Number of training epochs.
    max_checkpoints_to_keep: int
      Maximum number of checkpoints to keep; older checkpoints will be deleted.
    log_every_N_batches: int
      Report every N batches. Useful for training on very large datasets,
      where epochs can take long time to finish.

    Raises
    ------
    AssertionError
      If model is not in training mode.
    """
    time1 = time.time()
    log("Training for %d epochs" % nb_epoch, self.verbose)
    with self.train_graph.graph.as_default():
      train_op = self.get_training_op(
          self.train_graph.graph, self.train_graph.loss)
      with self._get_shared_session(train=True) as sess:
        sess.run(tf.global_variables_initializer())
        saver = tf.train.Saver(max_to_keep=max_checkpoints_to_keep)
        saver.save(sess, self._save_path, global_step=0)
        for epoch in range(nb_epoch):
          avg_loss, n_batches = 0., 0
          for ind, (X_b, y_b, w_b, ids_b) in enumerate(
              dataset.iterbatches(self.batch_size, pad_batches=self.pad_batches)):
            if ind % log_every_N_batches == 0:
              log("On batch %d" % ind, self.verbose)
            feed_dict = self.construct_feed_dict(X_b, y_b, w_b, ids_b)
            fetches = [train_op, self.train_graph.loss]
            fetched_values = sess.run(fetches, feed_dict=feed_dict)
            loss = fetched_values[-1]
            avg_loss += loss
            n_batches += 1
          saver.save(sess, self._save_path, global_step=epoch)
          avg_loss = float(avg_loss)/n_batches
          log('Ending epoch %d: Average loss %g' % (epoch, avg_loss), self.verbose)
        saver.save(sess, self._save_path, global_step=epoch+1)
    time2 = time.time()
    print("TIMING: model fitting took %0.3f s" % (time2-time1), self.verbose)

class TensorflowAdversarialMultiTaskRegressor(TensorflowMultiTaskRegressor):
  """ Adversarial training multitask regressor """

  def get_placeholders(self):
    
    n_features = self.n_features
    x = tf.placeholder(tf.float32, shape=[None, n_features], name='mol_features')
    return x

  def construct_graph(self, training, seed):
    """Returns a TensorflowGraph object."""
    graph = tf.Graph() 

    # Lazily created by _get_shared_session().
    shared_session = None

    # Cache of TensorFlow scopes, to prevent '_1' appended scope names
    # when subclass-overridden methods use the same scopes.
    name_scopes = {}
    eps = 0.1

    # Setup graph
    with graph.as_default():
      if seed is not None:
        tf.set_random_seed(seed)
      x = self.get_placeholders()
      output = self.model(graph, x, name_scopes, training)
      labels = self.add_label_placeholders(graph, name_scopes)
      weights = self.add_example_weight_placeholders(graph, name_scopes)

      if training:

        print("Constructing adversarial training graph")
        loss_1 = self.add_training_cost(graph, name_scopes, output, labels, weights)
        print("Calculated loss on true examples")
        grad, = tf.gradients(loss_1, x)
        signed_grad = tf.sign(grad)
        scaled_signed_grad = eps * signed_grad
        adv_x = tf.stop_gradient(x + scaled_signed_grad)
        adv_output = self.model(graph, adv_x, name_scopes, training)
        print("Calculated adversarial output")
        loss_2 = self.add_training_cost(graph, name_scopes, adv_output, labels, weights)
        print("Calculated loss on adversarial examples")
        loss = (loss_1 + loss_2)/2.

    if not training:
      loss = None
      output = self.add_output_ops(graph, output)  # add softmax heads
    return TensorflowGraph(graph=graph,
                           session=shared_session,
                           name_scopes=name_scopes,
                           output=output,
                           labels=labels,
                           weights=weights,
                           loss=loss)

  def model(self, graph, x, name_scopes, training):
    """Constructs the graph architecture as specified in its config.

    This method creates the following Placeholders:
      mol_features: Molecule descriptor (e.g. fingerprint) tensor with shape
        batch_size x n_features.
    """
    n_features = self.n_features
    with graph.as_default():
      
      layer_sizes = self.layer_sizes
      weight_init_stddevs = self.weight_init_stddevs
      bias_init_consts = self.bias_init_consts
      dropouts = self.dropouts
      lengths_set = {
          len(layer_sizes),
          len(weight_init_stddevs),
          len(bias_init_consts),
          len(dropouts),
      }
      assert len(lengths_set) == 1, 'All layer params must have same length.'
      n_layers = lengths_set.pop()
      assert n_layers > 0, 'Must have some layers defined.'

      prev_layer = x
      prev_layer_size = n_features
      for i in range(n_layers):
        layer = tf.nn.relu(
            model_ops.fully_connected_layer(
                tensor=prev_layer,
                size=layer_sizes[i],
                weight_init=tf.truncated_normal(
                    shape=[prev_layer_size, layer_sizes[i]],
                    stddev=weight_init_stddevs[i]),
                bias_init=tf.constant(
                    value=bias_init_consts[i], shape=[layer_sizes[i]])))
        layer = model_ops.dropout(layer, dropouts[i], training)
        prev_layer = layer
        prev_layer_size = layer_sizes[i]

      output = []
      for task in range(self.n_tasks):
        output.append(
            tf.squeeze(
                model_ops.fully_connected_layer(
                    tensor=prev_layer,
                    size=layer_sizes[i],
                    weight_init=tf.truncated_normal(
                        shape=[prev_layer_size, 1],
                        stddev=weight_init_stddevs[i]),
                    bias_init=tf.constant(value=bias_init_consts[i], shape=[1
                                                                           ]))))
      return output

class TensorflowMultiTaskFitTransformRegressor(TensorflowMultiTaskRegressor):
  """Implements a TensorflowMultiTaskRegressor that performs on-the-fly transformation during fit/predict

  Example:

  >>> n_samples = 10
  >>> n_features = 3
  >>> n_tasks = 1
  >>> ids = np.arange(n_samples)
  >>> X = np.random.rand(n_samples, n_features, n_features)
  >>> y = np.zeros((n_samples, n_tasks))
  >>> w = np.ones((n_samples, n_tasks))
  >>> dataset = dc.data.NumpyDataset(X, y, w, ids)
  >>> fit_transformers = [dc.trans.CoulombFitTransformer(dataset)]
  >>> model = dc.models.TensorflowMultiTaskFitTransformRegressor(n_tasks, [n_features, n_features],
  ...     dropouts=[0.], learning_rate=0.003, weight_init_stddevs=[np.sqrt(6)/np.sqrt(1000)],
  ...     batch_size=n_samples, fit_transformers=fit_transformers, n_evals=1)
  n_features after fit_transform: 12
  """

  def __init__(self,
               n_tasks,
               n_features,
               logdir=None,
               layer_sizes=[1000],
               weight_init_stddevs=[.02],
               bias_init_consts=[1.],
               penalty=0.0,
               penalty_type="l2",
               dropouts=[0.5],
               learning_rate=0.002,
               momentum=.8,
               optimizer="adam",
               batch_size=50,
               fit_transformers=[],
               n_evals=1,
               verbose=True,
               seed=None,
               **kwargs):
    """Initialize TensorflowMultiTaskFitTransformRegressor
       
    Parameters
    ----------
    n_tasks: int
      Number of tasks
    n_features: list or int
      Number of features.
    logdir: str
      Location to save data
    layer_sizes: list
      List of layer sizes.
    weight_init_stddevs: list
      List of standard deviations for weights (sampled from zero-mean
      gaussians). One for each layer.
    bias_init_consts: list
      List of bias initializations. One for each layer.
    penalty: float
      Amount of penalty (l2 or l1 applied)
    penalty_type: str
      Either "l2" or "l1"
    dropouts: list
      List of dropout amounts. One for each layer.
    learning_rate: float
      Learning rate for model.
    momentum: float
      Momentum. Only applied if optimizer=="momentum"
    optimizer: str
      Type of optimizer applied.
    batch_size: int
      Size of minibatches for training.
    fit_transformers: list
      List of dc.trans.FitTransformer objects
    n_evals: int
      Number of evalations per example at predict time
    verbose: True 
      Perform logging.
    seed: int
      If not none, is used as random seed for tensorflow.        

    """

    self.fit_transformers = fit_transformers
    self.n_evals = n_evals

    # Run fit transformers on dummy dataset to determine n_features after transformation
    if isinstance(n_features, list):
      X_b = np.ones([batch_size] + n_features)
    elif isinstance(n_features, int):
      X_b = np.ones([batch_size, n_features])
    else:
      raise ValueError("n_features should be list or int")

    for transformer in self.fit_transformers:
      X_b = transformer.X_transform(X_b)
    n_features = X_b.shape[1]
    print("n_features after fit_transform: %d" % int(n_features))

    TensorflowGraphModel.__init__(
        self,
        n_tasks,
        n_features,
        logdir=logdir,
        layer_sizes=layer_sizes,
        weight_init_stddevs=weight_init_stddevs,
        bias_init_consts=bias_init_consts,
        penalty=penalty,
        penalty_type=penalty_type,
        dropouts=dropouts,
        learning_rate=learning_rate,
        momentum=momentum,
        optimizer=optimizer,
        batch_size=batch_size,
        pad_batches=False,
        verbose=verbose,
        seed=seed,
        **kwargs)

  def fit(self,
          dataset,
          nb_epoch=10,
          max_checkpoints_to_keep=5,
          log_every_N_batches=50,
          **kwargs):
    """Perform fit transformations on each minibatch. Fit the model.

    Parameters
    ---------- 
    dataset: dc.data.Dataset
      Dataset object holding training data 
    nb_epoch: 10
      Number of training epochs.
    max_checkpoints_to_keep: int
      Maximum number of checkpoints to keep; older checkpoints will be deleted.
    log_every_N_batches: int
      Report every N batches. Useful for training on very large datasets,
      where epochs can take long time to finish.

    Raises
    ------
    AssertionError
      If model is not in training mode.
    """
    ############################################################## TIMING
    time1 = time.time()
    ############################################################## TIMING
    log("Training for %d epochs" % nb_epoch, self.verbose)
    with self.train_graph.graph.as_default():
      train_op = self.get_training_op(self.train_graph.graph,
                                      self.train_graph.loss)
      with self._get_shared_session(train=True) as sess:
        sess.run(tf.global_variables_initializer())
        saver = tf.train.Saver(max_to_keep=max_checkpoints_to_keep)
        # Save an initial checkpoint.
        saver.save(sess, self._save_path, global_step=0)
        for epoch in range(nb_epoch):
          avg_loss, n_batches = 0., 0
          for ind, (X_b, y_b, w_b, ids_b) in enumerate(
              dataset.iterbatches(
                  self.batch_size, pad_batches=self.pad_batches)):
            if ind % log_every_N_batches == 0:
              log("On batch %d" % ind, self.verbose)
            for transformer in self.fit_transformers:
              X_b = transformer.X_transform(X_b)
            # Run training op.
            feed_dict = self.construct_feed_dict(X_b, y_b, w_b, ids_b)
            fetches = self.train_graph.output + [
                train_op, self.train_graph.loss
            ]
            fetched_values = sess.run(fetches, feed_dict=feed_dict)
            output = fetched_values[:len(self.train_graph.output)]
            loss = fetched_values[-1]
            avg_loss += loss
            y_pred = np.squeeze(np.array(output))
            y_b = y_b.flatten()
            n_batches += 1
          saver.save(sess, self._save_path, global_step=epoch)
          avg_loss = float(avg_loss) / n_batches
          log('Ending epoch %d: Average loss %g' % (epoch, avg_loss),
              self.verbose)
        # Always save a final checkpoint when complete.
        saver.save(sess, self._save_path, global_step=epoch + 1)
    ############################################################## TIMING
    time2 = time.time()
    print("TIMING: model fitting took %0.3f s" % (time2 - time1), self.verbose)
    ############################################################## TIMING

  def predict_on_batch(self, X):
    """Return model output for the provided input. Each example is evaluated
        self.n_evals times.

    Restore(checkpoint) must have previously been called on this object.

    Args:
      dataset: dc.data.Dataset object.

    Returns:
      Tuple of three numpy arrays with shape n_examples x n_tasks (x ...):
        output: Model outputs.
        labels: True labels.
        weights: Example weights.
      Note that the output and labels arrays may be more than 2D, e.g. for
      classifier models that return class probabilities.

    Raises:
      AssertionError: If model is not in evaluation mode.
      ValueError: If output and labels are not both 3D or both 2D.
    """
    X_evals = []
    for i in range(self.n_evals):
      X_t = X
      for transformer in self.fit_transformers:
        X_t = transformer.X_transform(X_t)
      X_evals.append(X_t)
    len_unpadded = len(X_t)
    if self.pad_batches:
      for i in range(self.n_evals):
        X_evals[i] = pad_features(self.batch_size, X_evals[i])
    if not self._restored_model:
      self.restore()
    with self.eval_graph.graph.as_default():

      # run eval data through the model
      n_tasks = self.n_tasks
      outputs = []
      with self._get_shared_session(train=False).as_default():

        n_samples = len(X_evals[0])
        for i in range(self.n_evals):

          output = []
          feed_dict = self.construct_feed_dict(X_evals[i])
          data = self._get_shared_session(train=False).run(
              self.eval_graph.output, feed_dict=feed_dict)
          batch_outputs = np.asarray(data[:n_tasks], dtype=float)
          # reshape to batch_size x n_tasks x ...
          if batch_outputs.ndim == 3:
            batch_outputs = batch_outputs.transpose((1, 0, 2))
          elif batch_outputs.ndim == 2:
            batch_outputs = batch_outputs.transpose((1, 0))
          # Handle edge case when batch-size is 1.
          elif batch_outputs.ndim == 1:
            n_samples = len(X)
            batch_outputs = batch_outputs.reshape((n_samples, n_tasks))
          else:
            raise ValueError('Unrecognized rank combination for output: %s' %
                             (batch_outputs.shape))
          # Prune away any padding that was added
          batch_outputs = batch_outputs[:n_samples]
          output.append(batch_outputs)

          outputs.append(np.squeeze(np.concatenate(output)))

    outputs = np.mean(np.array(outputs), axis=0)
    outputs = np.copy(outputs)

    # Handle case of 0-dimensional scalar output
    if len(outputs.shape) > 0:
      return outputs[:len_unpadded]
    else:
      outputs = np.reshape(outputs, (1,))
      return outputs
