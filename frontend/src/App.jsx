import React, { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, InputNumber, Select, TimePicker, message, Popconfirm } from 'antd';
import { getPlans, createPlan, updatePlan, deletePlan } from './api';
import dayjs from 'dayjs';

const { Option } = Select;

const frequencyOptions = [
  { label: '每日', value: 'daily' },
  { label: '每周', value: 'weekly' },
  { label: '每月', value: 'monthly' },
];

const weekOptions = [
  { label: '周一', value: 0 },
  { label: '周二', value: 1 },
  { label: '周三', value: 2 },
  { label: '周四', value: 3 },
  { label: '周五', value: 4 },
  { label: '周六', value: 5 },
  { label: '周日', value: 6 },
];

export default function App() {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form] = Form.useForm();

  const fetchPlans = async () => {
    setLoading(true);
    try {
      const data = await getPlans();
      setPlans(data);
    } catch (e) {
      message.error('获取定投计划失败');
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchPlans();
  }, []);

  const handleAdd = () => {
    setEditing(null);
    form.resetFields();
    setModalOpen(true);
  };

  const handleEdit = (record) => {
    setEditing(record);
    form.setFieldsValue({
      ...record,
      time: dayjs(record.time, 'HH:mm'),
    });
    setModalOpen(true);
  };

  const handleDelete = async (id) => {
    await deletePlan(id);
    message.success('删除成功');
    fetchPlans();
  };

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      const payload = {
        ...values,
        time: values.time.format('HH:mm'),
      };
      if (editing) {
        await updatePlan(editing.id, payload);
        message.success('修改成功');
      } else {
        await createPlan(payload);
        message.success('添加成功');
      }
      setModalOpen(false);
      fetchPlans();
    } catch (e) {
      // 校验失败
    }
  };

  const columns = [
    { title: '币种', dataIndex: 'symbol' },
    { title: '金额', dataIndex: 'amount' },
    { title: '频率', dataIndex: 'frequency', render: v => frequencyOptions.find(o => o.value === v)?.label },
    { title: '周几', dataIndex: 'day_of_week', render: v => v !== null && v !== undefined ? weekOptions.find(o => o.value === v)?.label : '-' },
    { title: '时间', dataIndex: 'time' },
    { title: '状态', dataIndex: 'status' },
    { title: '操作', render: (_, record) => (
      <>
        <Button type="link" onClick={() => handleEdit(record)}>编辑</Button>
        <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
          <Button type="link" danger>删除</Button>
        </Popconfirm>
      </>
    ) },
  ];

  return (
    <div style={{ maxWidth: 900, margin: '40px auto', background: '#fff', padding: 24, borderRadius: 8 }}>
      <h2>OKX 定投计划管理</h2>
      <Button type="primary" onClick={handleAdd} style={{ marginBottom: 16 }}>新建定投计划</Button>
      <Table rowKey="id" columns={columns} dataSource={plans} loading={loading} bordered />
      <Modal
        title={editing ? '编辑定投计划' : '新建定投计划'}
        open={modalOpen}
        onOk={handleOk}
        onCancel={() => setModalOpen(false)}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="symbol" label="币种" rules={[{ required: true, message: '请输入币种，如 BTC-USDT' }]}> <Input placeholder="如 BTC-USDT" /> </Form.Item>
          <Form.Item name="amount" label="金额" rules={[{ required: true, message: '请输入金额' }]}> <InputNumber min={0.01} style={{ width: '100%' }} /> </Form.Item>
          <Form.Item name="frequency" label="频率" rules={[{ required: true, message: '请选择频率' }]}> <Select options={frequencyOptions} /> </Form.Item>
          <Form.Item name="day_of_week" label="周几（仅每周时填写）"> <Select allowClear options={weekOptions} /> </Form.Item>
          <Form.Item name="time" label="时间" rules={[{ required: true, message: '请选择时间' }]}> <TimePicker format="HH:mm" /> </Form.Item>
        </Form>
      </Modal>
    </div>
  );
} 