import numpy as np
import tensorflow as tf


def gmm_tensorflow(COMPONENTS, DIMENSIONS, TRAINING_STEPS, TOLERANCE, beta_nonparam):
    # BUILDING COMPUTATIONAL GRAPH
    # model inputs: data points and prior parameters
    input = tf.placeholder(tf.float64, [None, dimensions])
    alpha = tf.placeholder_with_default(tf.cast(1.0, tf.float64), [])
    beta = tf.placeholder_with_default(tf.cast(1.0, tf.float64), [])
    # constants: ln(2 * PI) * D
    ln2piD = tf.constant(np.log(2 * np.pi) * dimensions, dtype=tf.float64)
    # computing input statistics
    dim_means = tf.reduce_mean(input, 0)
    dim_distances = tf.squared_difference(input, tf.expand_dims(dim_means, 0))
    dim_variances = tf.reduce_sum(dim_distances, 0) / tf.cast(tf.shape(input)[0], tf.float64)
    avg_dim_variance = tf.cast(tf.reduce_sum(dim_variances) / COMPONENTS / dimensions, tf.float64)
    # default initial values of the variables
    initial_means = tf.placeholder_with_default(tf.gather(input, tf.squeeze(tf.multinomial(tf.ones([1, tf.shape(input)[0]]), COMPONENTS))),shape=[COMPONENTS, dimensions])
    initial_covariances = tf.placeholder_with_default(tf.eye(dimensions, batch_shape=[COMPONENTS], dtype=tf.float64) * avg_dim_variance,shape=[COMPONENTS, dimensions, dimensions])
    initial_weights = tf.placeholder_with_default(tf.cast(tf.constant(1.0 / COMPONENTS, shape=[COMPONENTS]), tf.float64),shape=[COMPONENTS])
    # trainable variables: component means, covariances, and weights
    means = tf.Variable(initial_means, dtype=tf.float64)
    covariances = tf.Variable(initial_covariances, dtype=tf.float64)
    weights = tf.Variable(initial_weights, dtype=tf.float64)
    # E-step: recomputing responsibilities with respect to the current parameter values
    differences = tf.subtract(tf.expand_dims(input, 0), tf.expand_dims(means, 1))
    diff_times_inv_cov = tf.matmul(differences, tf.matrix_inverse(covariances))
    sum_sq_dist_times_inv_cov = tf.reduce_sum(diff_times_inv_cov * differences, 2)
    log_coefficients = tf.expand_dims(ln2piD + tf.log(tf.matrix_determinant(covariances)), 1)
    log_components = -0.5 * (log_coefficients + sum_sq_dist_times_inv_cov)
    log_weighted = log_components + tf.expand_dims(tf.log(weights), 1)
    log_shift = tf.expand_dims(tf.reduce_max(log_weighted, 0), 0)
    exp_log_shifted = tf.exp(log_weighted - log_shift)
    exp_log_shifted_sum = tf.reduce_sum(exp_log_shifted, 0)
    gamma = exp_log_shifted / exp_log_shifted_sum
    # M-step: maximizing parameter values with respect to the computed responsibilities
    gamma_sum = tf.reduce_sum(gamma, 1)
    gamma_weighted = gamma / tf.expand_dims(gamma_sum, 1)
    means_ = tf.reduce_sum(tf.expand_dims(input, 0) * tf.expand_dims(gamma_weighted, 2), 1)
    differences_ = tf.subtract(tf.expand_dims(input, 0), tf.expand_dims(means_, 1))
    sq_dist_matrix = tf.matmul(tf.expand_dims(differences_, 3), tf.expand_dims(differences_, 2))
    covariances_ = tf.reduce_sum(sq_dist_matrix * tf.expand_dims(tf.expand_dims(gamma_weighted, 2), 3), 1)
    weights_ = gamma_sum / tf.cast(tf.shape(input)[0], tf.float64)
    # applying prior to the computed covariances
    covariances_ *= tf.expand_dims(tf.expand_dims(gamma_sum, 1), 2)
    covariances_ += tf.expand_dims(tf.diag(tf.fill([dimensions], 2.0 * beta)), 0)
    covariances_ /= tf.expand_dims(tf.expand_dims(gamma_sum + (2.0 * (alpha + 1.0)), 1), 2)
    # log-likelihood: objective function being maximized up to a TOLERANCE delta
    log_likelihood = tf.reduce_sum(tf.log(exp_log_shifted_sum)) + tf.reduce_sum(log_shift)
    mean_log_likelihood = log_likelihood / tf.cast(tf.shape(input)[0] * tf.shape(input)[1], tf.float64)
    # assigning new values to the parameters
    train_step = tf.group(means.assign(means_),covariances.assign(covariances_),weights.assign(weights_))
    # RUNNING COMPUTATIONAL GRAPH
    with tf.Session() as sess:
        # initializing trainable variables
        sess.run(tf.global_variables_initializer(),  feed_dict={input: beta_nonparam,initial_means: beta_nonparam[:10] })
        previous_likelihood = -np.inf
        # training loop
        for step in range(TRAINING_STEPS):
            # executing a training step and
            # fetching evaluation information
            current_likelihood, _ = sess.run([mean_log_likelihood, train_step],feed_dict={input: beta_nonparam})
            if step > 0:
                # computing difference between consecutive log-likelihoods
                difference = np.abs(current_likelihood - previous_likelihood)
                print("{0}:\tmean-likelihood {1:.8f}\tdifference {2}".format(step, current_likelihood, difference))
                # stopping if TOLERANCE was reached
                if difference <= TOLERANCE:
                    break
            else:
                print("{0}:\tmean-likelihood {1:.8f}".format(step, current_likelihood))
            previous_likelihood = current_likelihood
        # fetching final parameter values
        final_means = means.eval(sess)
        final_covariances = covariances.eval(sess)
        return final_means
