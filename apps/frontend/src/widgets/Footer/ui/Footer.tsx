import React from 'react';
import { Container, Flex } from '@chakra-ui/react';

const Footer = () => {
  return (
    <Container
      borderTop="1px solid gray"
      height="60px"
      fontFamily="Faculty Glyphic">
      <Flex justifyContent="space-between" alignItems="center" height="100%">
        <p>Papaya 2026</p>
      </Flex>
    </Container>
  );
};

export default Footer;
